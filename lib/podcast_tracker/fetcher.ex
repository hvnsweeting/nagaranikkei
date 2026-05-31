defmodule PodcastTracker.Fetcher do
  require Logger
  import SweetXml
  alias PodcastTracker.Podcasts

  @rss_url "https://feeds.megaphone.fm/nagara"

  def run do
    Logger.info("Fetching podcast RSS from #{@rss_url}")

    # Cognitive load: Use clear intermediate variables
    response = Req.get!(@rss_url, receive_timeout: 10_000)
    xml_body = response.body

    parsed_xml = SweetXml.parse(xml_body, dtd: :none)
    first_item = parsed_xml |> xpath(~x"//item[1]")
    title = first_item |> xpath(~x"./title/text()"s)
    pub_date_str = first_item |> xpath(~x"./pubDate/text()"s)

    # Extract audio URL or link
    link = first_item |> xpath(~x"./link/text()"s)
    enclosure_url = first_item |> xpath(~x"./enclosure/@url"s)
    audio_url = if(is_nil(link) or String.trim(link) == "", do: enclosure_url, else: link)

    if is_nil(title) or String.trim(title) == "" do
      Logger.error(
        "Failed to extract title from RSS feed. Body snippet: #{String.slice(xml_body, 0, 100)}"
      )

      :error
    else
      parsed_date = parse_date(pub_date_str)

      # Check if episode already exists in DB
      existing_episode = Podcasts.get_episode_by_title(title)
      is_new = is_nil(existing_episode)

      if is_new do
        case process_new_episode(title, parsed_date, audio_url) do
          {:ok, _} ->
            Logger.info("New episode successfully processed: #{title}")

          {:error, changeset} ->
            Logger.warning(
              "Failed to insert new episode (potential race win): #{inspect(changeset.errors)}"
            )
        end
      else
        Logger.info("Episode already exists: #{title}")
      end
    end
  end

  defp process_new_episode(title, pub_date, audio_url) do
    Logger.info("Processing new episode: #{title}")

    # Cognitive load: separating analysis from persistence
    {english_title, chunks} = analyze_japanese(title)

    case Podcasts.create_episode(%{
           japanese_title: title,
           english_translation: english_title,
           published_at: pub_date,
           audio_url: audio_url
         }) do
      {:ok, episode} ->
        chunks
        |> Enum.with_index()
        |> Enum.each(fn {chunk, index} ->
          Podcasts.create_chunk(episode, %{
            japanese_text: chunk.japanese,
            romaji: chunk.romaji,
            english_meaning: chunk.meaning,
            order_index: index
          })
        end)

        Logger.info("Episode saved successfully.")
        {:ok, episode}

      {:error, changeset} ->
        {:error, changeset}
    end
  end

  defp analyze_japanese(text) do
    api_key =
      System.get_env("GEMINI_API_KEY") ||
        System.get_env("GEMINI_API_TOKEN") ||
        read_from_env_file("GEMINI_API_KEY") ||
        read_from_env_file("GEMINI_API_TOKEN")

    if is_nil(api_key) or api_key == "" do
      Logger.warning("GEMINI_API_KEY is not set. Using mock translation.")
      mock_analyze(text)
    else
      call_llm(text, api_key)
    end
  end

  defp call_llm(text, api_key) do
    models = [
      "gemini-2.5-flash",
      "gemini-2.5-flash-lite",
      "gemini-flash-latest",
      "gemini-flash-lite-latest",
      "gemini-3.5-flash",
      "gemini-2.0-flash",
      "gemini-2.0-flash-lite"
    ]

    case try_models(models, text, api_key) do
      {:ok, result} ->
        result

      {:error, reason} ->
        Logger.error("All Gemini models failed. Reason: #{reason}. Using mock translation.")
        mock_analyze(text)
    end
  end

  defp try_models([], _text, _api_key) do
    {:error, "No more models left to try"}
  end

  defp try_models([model | rest], text, api_key) do
    Logger.info("Attempting translation with Gemini model: #{model}...")

    prompt = """
    You are a Japanese learning assistant. I will provide a Japanese podcast title. 
    1. Translate the full title to English.
    2. Break the title down word by word or phrase by phrase. For each chunk, provide the Japanese text, Romaji reading, and English meaning.

    Output strictly in the following JSON format:
    {
      "english_translation": "Full english translation of the title",
      "chunks": [
        {"japanese": "...", "romaji": "...", "meaning": "..."}
      ]
    }

    Title: #{text}
    """

    req_body = %{
      "contents" => [
        %{
          "parts" => [%{"text" => prompt}]
        }
      ],
      "generationConfig" => %{
        "responseMimeType" => "application/json"
      }
    }

    url =
      "https://generativelanguage.googleapis.com/v1beta/models/#{model}:generateContent?key=#{api_key}"

    try do
      case Req.post(url, json: req_body, receive_timeout: 30_000) do
        {:ok, %{status: 200, body: body}} ->
          # Extract the text content from Gemini's response
          text_content =
            get_in(body, ["candidates", Access.at(0), "content", "parts", Access.at(0), "text"])

          case Jason.decode(text_content) do
            {:ok, parsed} ->
              english = parsed["english_translation"]

              chunks =
                Enum.map(parsed["chunks"] || [], fn c ->
                  %{
                    japanese: c["japanese"],
                    romaji: c["romaji"],
                    meaning: c["meaning"]
                  }
                end)

              if is_nil(english) or english == "" or Enum.empty?(chunks) do
                Logger.warning(
                  "Model #{model} returned empty translation or chunks. Trying next model."
                )

                try_models(rest, text, api_key)
              else
                Logger.info("Successfully translated using #{model}")
                {:ok, {english, chunks}}
              end

            _ ->
              Logger.warning("Failed to parse JSON response from #{model}. Trying next model.")
              try_models(rest, text, api_key)
          end

        {:ok, %{status: status, body: body}} ->
          Logger.warning(
            "Model #{model} failed with status #{status}: #{get_in(body, ["error", "message"]) || inspect(body)}. Trying next model."
          )

          try_models(rest, text, api_key)

        {:error, reason} ->
          Logger.warning(
            "Model #{model} failed with network error: #{inspect(reason)}. Trying next model."
          )

          try_models(rest, text, api_key)
      end
    rescue
      e ->
        Logger.warning("Model #{model} raised exception: #{inspect(e)}. Trying next model.")
        try_models(rest, text, api_key)
    end
  end

  defp mock_analyze(text) do
    mock_english = "Daily Nikkei News: " <> String.slice(text, 0..10) <> "..."

    mock_chunks = [
      %{japanese: "日経", romaji: "nikkei", meaning: "Nikkei (newspaper)"},
      %{japanese: "平均", romaji: "heikin", meaning: "Average"},
      %{japanese: "は", romaji: "wa", meaning: "is (particle)"},
      %{japanese: "反落", romaji: "hanraku", meaning: "fell back / declined"}
    ]

    {mock_english, mock_chunks}
  end

  defp parse_date(date_str) do
    # Input example: "Mon, 01 Jan 2024 12:00:00 +0000"
    try do
      case apply(Calendar.ISO, :parse_rfc2822, [date_str]) do
        {:ok, {year, month, day, hour, minute, second, _gmt_offset}} ->
          case NaiveDateTime.new(year, month, day, hour, minute, second) do
            {:ok, ndt} -> ndt
            _ -> parse_date_regex(date_str)
          end

        _ ->
          parse_date_regex(date_str)
      end
    rescue
      _ -> parse_date_regex(date_str)
    end
  end

  defp parse_date_regex(date_str) do
    months = %{
      "Jan" => 1,
      "Feb" => 2,
      "Mar" => 3,
      "Apr" => 4,
      "May" => 5,
      "Jun" => 6,
      "Jul" => 7,
      "Aug" => 8,
      "Sep" => 9,
      "Oct" => 10,
      "Nov" => 11,
      "Dec" => 12
    }

    case Regex.run(
           ~r/(?:[A-Za-z]{3},\s+)?(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})\s+(\d{2}):(\d{2}):(\d{2})/,
           date_str
         ) do
      [_, day_str, month_str, year_str, hour_str, minute_str, second_str] ->
        year = String.to_integer(year_str)
        month = Map.get(months, month_str, 1)
        day = String.to_integer(day_str)
        hour = String.to_integer(hour_str)
        minute = String.to_integer(minute_str)
        second = String.to_integer(second_str)

        case NaiveDateTime.new(year, month, day, hour, minute, second) do
          {:ok, ndt} -> ndt
          _ -> NaiveDateTime.truncate(NaiveDateTime.utc_now(), :second)
        end

      _ ->
        Logger.warning(
          "Failed to parse pubDate str: '#{date_str}'. Falling back to current timestamp."
        )

        NaiveDateTime.truncate(NaiveDateTime.utc_now(), :second)
    end
  end

  defp read_from_env_file(key) do
    case File.read(".env") do
      {:ok, content} ->
        content
        |> String.split("\n")
        |> Enum.find_value(nil, fn line ->
          case String.split(line, "=", parts: 2) do
            [^key, value] ->
              value |> String.trim() |> String.trim("\"") |> String.trim("'")

            _ ->
              nil
          end
        end)

      _ ->
        nil
    end
  end
end
