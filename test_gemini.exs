Mix.install([
  {:req, "~> 0.5.0"},
  {:jason, "~> 1.4"}
])

api_key = System.get_env("GEMINI_API_KEY") || "PLACEHOLDER_KEY"

models = [
  "gemini-3.5-flash",
  "gemini-2.5-flash",
  "gemini-2.5-flash-lite",
  "gemini-2.0-flash",
  "gemini-2.0-flash-lite",
  "gemini-flash-latest",
  "gemini-flash-lite-latest"
]

Enum.each(models, fn model ->
  req_body = %{"contents" => [%{"parts" => [%{"text" => "hello"}]}]}

  url =
    "https://generativelanguage.googleapis.com/v1beta/models/#{model}:generateContent?key=#{api_key}"

  try do
    case Req.post(url, json: req_body) do
      {:ok, %{status: 200, body: _body}} ->
        IO.puts("SUCCESS: #{model}")

      {:ok, %{status: status, body: body}} ->
        IO.puts(
          "FAILED: #{model} with status #{status}: #{get_in(body, ["error", "status"]) || inspect(body)}"
        )

      {:error, err} ->
        IO.puts("ERROR: #{model}: #{inspect(err)}")
    end
  rescue
    e -> IO.puts("EXC: #{model}: #{inspect(e)}")
  end
end)
