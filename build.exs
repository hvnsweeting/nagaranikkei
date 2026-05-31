# Single-file Static Generator for zero-cost GitHub Pages hosting
# Run via: mix run build.exs

defmodule PodcastTracker.StaticGenerator do
  require Logger
  import SweetXml

  @rss_url "https://feeds.megaphone.fm/nagara"
  @history_file "history.json"
  @dist_dir "dist"

  def run do
    Logger.info("Starting PodcastTracker Static Site Generator...")
    File.mkdir_p!(@dist_dir)

    # 1. Load history database
    history = load_history()

    # 2. Fetch Megaphone RSS
    Logger.info("Fetching RSS from #{@rss_url}")
    response = Req.get!(@rss_url, receive_timeout: 10_000)
    xml_body = response.body

    parsed_xml = SweetXml.parse(xml_body, dtd: :none)
    first_item = parsed_xml |> xpath(~x"//item[1]")
    title = first_item |> xpath(~x"./title/text()"s)
    pub_date_str = first_item |> xpath(~x"./pubDate/text()"s)

    link = first_item |> xpath(~x"./link/text()"s)
    enclosure_url = first_item |> xpath(~x"./enclosure/@url"s)
    audio_url = if(is_nil(link) or String.trim(link) == "", do: enclosure_url, else: link)

    if is_nil(title) or String.trim(title) == "" do
      Logger.error("Failed to parse RSS feed.")
    else
      parsed_date = parse_date(pub_date_str)

      # 3. Check if episode already exists in our history
      existing_index = Enum.find_index(history, fn ep -> ep["japanese_title"] == title end)

      updated_history =
        if is_nil(existing_index) do
          Logger.info("Found new episode: #{title}")

          # 4. Hit Gemini API with model fallbacks
          case analyze_japanese(title) do
            {:ok, {english, chunks}} ->
              new_episode = %{
                "japanese_title" => title,
                "english_translation" => english,
                "published_at" => NaiveDateTime.to_string(parsed_date),
                "audio_url" => audio_url,
                "chunks" => chunks
              }

              # Limit history to latest 100 items to save space
              [new_episode | history] |> Enum.take(100)

            _ ->
              Logger.error("Failed to analyze new episode. Skipping update.")
              history
          end
        else
          Logger.info("Episode already exists in history.")
          history
        end

      # 5. Save history database
      save_history(updated_history)

      # 6. Generate static index.html dashboard
      generate_html(updated_history)

      # 7. Generate static rss.xml feed for RSS readers
      generate_rss(updated_history)

      Logger.info("Static build completed successfully in the '#{@dist_dir}' folder!")
    end
  end

  # JSON Database Helpers
  defp load_history do
    if File.exists?(@history_file) do
      case File.read(@history_file) do
        {:ok, content} ->
          case Jason.decode(content) do
            {:ok, parsed} -> parsed
            _ -> []
          end

        _ ->
          []
      end
    else
      []
    end
  end

  defp save_history(history) do
    {:ok, json} = Jason.encode(history, pretty: true)
    File.write!(@history_file, json)
  end

  # Gemini API with recursive model fallbacks
  defp analyze_japanese(text) do
    api_key =
      System.get_env("GEMINI_API_KEY") ||
        System.get_env("GEMINI_API_TOKEN") ||
        read_from_env_file("GEMINI_API_KEY") ||
        read_from_env_file("GEMINI_API_TOKEN")

    if is_nil(api_key) or api_key == "" do
      Logger.warning("GEMINI_API_KEY not set. Using mock translation.")
      {:ok, mock_analyze(text)}
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
        {:ok, result}

      {:error, reason} ->
        Logger.error("All models failed: #{reason}. Using mock.")
        {:ok, mock_analyze(text)}
    end
  end

  defp try_models([], _text, _api_key) do
    {:error, "No more models left to try"}
  end

  defp try_models([model | rest], text, api_key) do
    Logger.info("Attempting translation with model: #{model}...")

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
      "contents" => [%{"parts" => [%{"text" => prompt}]}],
      "generationConfig" => %{"responseMimeType" => "application/json"}
    }

    url =
      "https://generativelanguage.googleapis.com/v1beta/models/#{model}:generateContent?key=#{api_key}"

    try do
      case Req.post(url, json: req_body, receive_timeout: 30_000) do
        {:ok, %{status: 200, body: body}} ->
          text_content =
            get_in(body, ["candidates", Access.at(0), "content", "parts", Access.at(0), "text"])

          case Jason.decode(text_content) do
            {:ok, parsed} ->
              english = parsed["english_translation"]

              chunks =
                Enum.map(parsed["chunks"] || [], fn c ->
                  %{
                    "japanese" => c["japanese"],
                    "romaji" => c["romaji"],
                    "meaning" => c["meaning"]
                  }
                end)

              if is_nil(english) or english == "" or Enum.empty?(chunks) do
                try_models(rest, text, api_key)
              else
                Logger.info("Successfully translated using #{model}")
                {:ok, {english, chunks}}
              end

            _ ->
              try_models(rest, text, api_key)
          end

        _ ->
          try_models(rest, text, api_key)
      end
    rescue
      _ -> try_models(rest, text, api_key)
    end
  end

  defp mock_analyze(text) do
    mock_english = "Daily Nikkei News: " <> String.slice(text, 0..10) <> "..."

    mock_chunks = [
      %{"japanese" => "日経", "romaji" => "nikkei", "meaning" => "Nikkei (newspaper)"},
      %{"japanese" => "平均", "romaji" => "heikin", "meaning" => "Average"},
      %{"japanese" => "は", "romaji" => "wa", "meaning" => "is (particle)"},
      %{"japanese" => "反落", "romaji" => "hanraku", "meaning" => "fell back / declined"}
    ]

    {mock_english, mock_chunks}
  end

  # RFC 2822 date parser
  defp parse_date(date_str) do
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
            [^key, value] -> value |> String.trim() |> String.trim("\"") |> String.trim("'")
            _ -> nil
          end
        end)

      _ ->
        nil
    end
  end

  # HTML static builder
  defp generate_html(episodes) do
    cards_html =
      if Enum.empty?(episodes) do
        """
        <div class="empty-state">
          <p>No episodes translated yet. Running the workflow will fetch the latest!</p>
        </div>
        """
      else
        episodes
        |> Enum.map(fn ep ->
          chunks_html =
            ep["chunks"]
            |> Enum.map(fn c ->
              """
              <div class="chunk">
                <dt>
                  <a href="https://jisho.org/search/#{URI.encode_www_form(c["japanese"])}" target="_blank" rel="noopener noreferrer" class="chunk-jp-link">
                    <span class="chunk-jp">#{escape_html(c["japanese"])}</span>
                  </a>
                  <span class="chunk-ro">#{escape_html(c["romaji"])}</span>
                </dt>
                <dd class="chunk-en">#{escape_html(c["meaning"])}</dd>
              </div>
              """
            end)
            |> Enum.join("\n")

          date_formatted = String.slice(ep["published_at"], 0, 10)

          """
          <div class="episode-card">
            <span class="date">#{escape_html(date_formatted)}</span>
            <h2 class="japanese-title">
              #{escape_html(ep["japanese_title"])}
              <a href="#{escape_html(ep["audio_url"] || "https://www.radionikkei.jp/nagara/")}" target="_blank" rel="noopener noreferrer" class="listen-badge">
                Listen
              </a>
            </h2>
            <p class="english-title">#{escape_html(ep["english_translation"])}</p>

            <dl class="chunks-container">
              #{chunks_html}
            </dl>
          </div>
          """
        end)
        |> Enum.join("\n")
      end

    html_content = """
    <!DOCTYPE html>
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>ながら日経 Podcast Tracker</title>
        <style>
          @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');

          :root {
            --bg-color: #0f172a;
            --card-bg: #1e293b;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --accent: #38bdf8;
            --accent-glow: rgba(56, 189, 248, 0.2);
            --border-color: #334155;
          }
          body {
            background-color: var(--bg-color);
            color: var(--text-main);
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            margin: 0;
            padding: 0;
            line-height: 1.6;
            -webkit-font-smoothing: antialiased;
          }
          .container {
            max-width: 800px;
            margin: 0 auto;
            padding: 40px 20px;
          }
          header {
            text-align: center;
            margin-bottom: 50px;
          }
          h1 {
            font-size: 2.5rem;
            margin: 0;
            background: linear-gradient(135deg, #38bdf8, #818cf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
          }
          p.subtitle {
            color: var(--text-muted);
            font-size: 1.1rem;
          }
          .episode-card {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
          }
          .date {
            font-size: 0.9rem;
            color: var(--accent);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
            display: block;
          }
          .japanese-title {
            font-size: 1.5rem;
            margin: 0 0 10px 0;
            font-weight: 600;
            letter-spacing: 0.5px;
          }
          .english-title {
            font-size: 1.1rem;
            color: var(--text-muted);
            margin: 0 0 25px 0;
            font-style: italic;
          }
          .chunks-container {
            display: flex;
            flex-direction: column;
            background: rgba(255, 255, 255, 0.01);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            overflow: hidden;
            margin-top: 15px;
            margin-bottom: 0;
            padding: 0;
          }
          .chunk {
            display: grid;
            grid-template-columns: 220px 1fr;
            align-items: center;
            gap: 20px;
            padding: 16px 20px;
            border-bottom: 1px solid var(--border-color);
            margin: 0;
            transition: background-color 0.2s ease;
            cursor: default;
          }
          .chunk:last-child {
            border-bottom: none;
          }
          .chunk:hover {
            background-color: rgba(255, 255, 255, 0.03);
          }
          .chunk dt, .chunk dd {
            margin: 0;
            padding: 0;
          }
          .chunk dt {
            display: flex;
            flex-direction: column;
            gap: 4px;
          }
          .chunk-jp-link {
            text-decoration: none;
            color: #fff;
            transition: color 0.2s ease;
          }
          .chunk-jp-link:hover {
            color: var(--accent);
            text-decoration: underline;
          }
          .chunk-jp {
            font-size: 1.25rem;
            font-weight: 600;
            color: inherit;
          }
          .chunk-ro {
            font-size: 0.85rem;
            color: var(--accent);
            letter-spacing: 0.5px;
          }
          .chunk-en {
            font-size: 1rem;
            color: var(--text-main);
            line-height: 1.5;
          }
          .listen-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: var(--accent-glow);
            border: 1px solid var(--accent);
            color: var(--accent);
            font-size: 0.85rem;
            padding: 4px 12px;
            border-radius: 9999px;
            margin-left: 12px;
            text-decoration: none;
            vertical-align: middle;
            font-weight: 500;
            transition: background-color 0.2s ease, transform 0.2s ease;
          }
          .listen-badge:hover {
            background: var(--accent);
            color: var(--bg-color);
            transform: scale(1.05);
          }
          .empty-state {
            text-align: center;
            padding: 50px;
            color: var(--text-muted);
            border: 1px dashed var(--border-color);
            border-radius: 16px;
          }
          .rss-info {
            text-align: center;
            margin-top: 40px;
            padding: 20px;
            background: rgba(255,255,255,0.02);
            border: 1px solid var(--border-color);
            border-radius: 12px;
          }
          .rss-link {
            color: var(--accent);
            font-weight: 600;
            text-decoration: none;
          }
          .rss-link:hover {
            text-decoration: underline;
          }
          .pagination-container {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 20px;
            margin-top: 40px;
            margin-bottom: 20px;
          }
          .page-btn {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            color: var(--text-main);
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            transition: background-color 0.2s ease, border-color 0.2s ease;
          }
          .page-btn:hover:not(:disabled) {
            background: rgba(255, 255, 255, 0.05);
            border-color: var(--accent);
          }
          .page-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
          }
          .page-info {
            font-size: 1rem;
            color: var(--text-muted);
            font-weight: 500;
          }
          @media (max-width: 600px) {
            .chunk {
              grid-template-columns: 1fr;
              gap: 8px;
              padding: 14px 16px;
            }
            .listen-badge {
              margin-left: 0;
              margin-top: 8px;
              display: inline-flex;
            }
          }
        </style>
      </head>
      <body>
        <div class="container">
          <header>
            <h1>ながら日経 Tracker</h1>
            <p class="subtitle">Daily Japanese learning through podcast titles</p>
          </header>

          <main>
            #{cards_html}
          </main>

          <div class="pagination-container" id="pagination-controls">
            <button id="prev-btn" class="page-btn">Previous</button>
            <span id="page-info" class="page-info">Page 1 of 1</span>
            <button id="next-btn" class="page-btn">Next</button>
          </div>

          <footer class="rss-info">
            <p>💡 Want to learn inside your favorite RSS reader? Subscribe to our custom vocabulary feed:</p>
            <p>🔗 <a class="rss-link" href="rss.xml" target="_blank">Subscribe to rss.xml Feed</a></p>
          </footer>
        </div>

        <script>
          document.addEventListener('DOMContentLoaded', () => {
            const episodesPerPage = 5;
            let currentPage = 1;
            const cards = document.querySelectorAll('.episode-card');
            const totalPages = Math.ceil(cards.length / episodesPerPage);
            const controls = document.getElementById('pagination-controls');

            if (cards.length === 0) {
              if (controls) controls.style.display = 'none';
              return;
            }

            function showPage(page) {
              if (page < 1) page = 1;
              if (page > totalPages) page = totalPages;
              currentPage = page;

              const start = (currentPage - 1) * episodesPerPage;
              const end = start + episodesPerPage;

              cards.forEach((card, index) => {
                if (index >= start && index < end) {
                  card.style.display = 'block';
                  card.style.opacity = '0';
                  card.style.transition = 'none';
                  requestAnimationFrame(() => {
                    card.style.transition = 'opacity 0.4s ease';
                    card.style.opacity = '1';
                  });
                } else {
                  card.style.display = 'none';
                }
              });

              document.getElementById('page-info').textContent = `Page ${currentPage} of ${totalPages}`;
              document.getElementById('prev-btn').disabled = (currentPage === 1);
              document.getElementById('next-btn').disabled = (currentPage === totalPages);
              window.scrollTo({ top: 0, behavior: 'smooth' });
            }

            document.getElementById('prev-btn').addEventListener('click', () => showPage(currentPage - 1));
            document.getElementById('next-btn').addEventListener('click', () => showPage(currentPage + 1));

            showPage(1);
          });
        </script>
      </body>
    </html>
    """

    File.write!(Path.join(@dist_dir, "index.html"), html_content)
  end

  # RSS XML feed builder
  defp generate_rss(episodes) do
    items_xml =
      episodes
      |> Enum.map(fn ep ->
        table_rows =
          ep["chunks"]
          |> Enum.map(fn c ->
            """
            <tr>
              <td style="padding: 8px; border-bottom: 1px solid #334155; font-weight: bold; font-size: 1.1em;">#{escape_html(c["japanese"])}</td>
              <td style="padding: 8px; border-bottom: 1px solid #334155; color: #38bdf8;">#{escape_html(c["romaji"])}</td>
              <td style="padding: 8px; border-bottom: 1px solid #334155;">#{escape_html(c["meaning"])}</td>
            </tr>
            """
          end)
          |> Enum.join("\n")

        description_html = """
        <p><strong>English Title:</strong> <em>#{escape_html(ep["english_translation"])}</em></p>
        <h3>Vocabulary Breakdown:</h3>
        <table style="width: 100%; border-collapse: collapse; text-align: left;">
          <thead>
            <tr style="background-color: #1e293b; color: #f8fafc;">
              <th style="padding: 8px;">Japanese</th>
              <th style="padding: 8px;">Romaji</th>
              <th style="padding: 8px;">English Meaning</th>
            </tr>
          </thead>
          <tbody>
            #{table_rows}
          </tbody>
        </table>
        <p><a href="#{escape_html(ep["audio_url"] || "https://www.radionikkei.jp/nagara/")}">Listen to this Episode on Radio NIKKEI</a></p>
        """

        # Escape HTML for XML compliance
        escaped_description =
          description_html
          |> String.replace("&", "&amp;")
          |> String.replace("<", "&lt;")
          |> String.replace(">", "&gt;")
          |> String.replace("\"", "&quot;")
          |> String.replace("'", "&apos;")

        escaped_title = escape_html("#{ep["japanese_title"]} - #{ep["english_translation"]}")
        escaped_link = escape_html(ep["audio_url"] || "https://www.radionikkei.jp/nagara/")
        escaped_guid = escape_html(ep["japanese_title"])
        escaped_pub_date = escape_html(ep["published_at"])

        """
        <item>
          <title>#{escaped_title}</title>
          <link>#{escaped_link}</link>
          <guid isPermaLink="false">#{escaped_guid}</guid>
          <pubDate>#{escaped_pub_date} +0000</pubDate>
          <description>#{escaped_description}</description>
        </item>
        """
      end)
      |> Enum.join("\n")

    rss_content = """
    <?xml version="1.0" encoding="UTF-8" ?>
    <rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
    <channel>
      <title>ながら日経 Vocabulary Tracker</title>
      <link>https://www.radionikkei.jp/nagara/</link>
      <description>Daily Japanese learning chunks, romaji, and translations from the latest Nagara Nikkei podcast titles.</description>
      <language>en-us</language>
      #{items_xml}
    </channel>
    </rss>
    """

    File.write!(Path.join(@dist_dir, "rss.xml"), rss_content)
  end

  defp escape_html(nil), do: ""

  defp escape_html(text) when is_binary(text) do
    text
    |> String.replace("&", "&amp;")
    |> String.replace("<", "&lt;")
    |> String.replace(">", "&gt;")
    |> String.replace("\"", "&quot;")
    |> String.replace("'", "&#39;")
  end
end

# Trigger execution immediately
PodcastTracker.StaticGenerator.run()
