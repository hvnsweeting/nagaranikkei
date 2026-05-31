defmodule Mix.Tasks.Secrets.Scan do
  use Mix.Task

  @shortdoc "Scans the codebase for leaked secrets and API keys"

  # Regex patterns for common secrets (e.g. Google Gemini API keys)
  @patterns %{
    "Google/Gemini API Key" => ~r/AIzaSy[A-Za-z0-9_\-]{33}/
  }

  # Directories and files to exclude from scanning
  @excludes [
    ~r|^\.git/|,
    ~r|^_build/|,
    ~r|^deps/|,
    ~r|^dist/|,
    ~r|^\.env$|,
    ~r|^history\.json$|,
    ~r|^mix\.lock$|
  ]

  @impl Mix.Task
  def run(_args) do
    IO.puts("==> Running Secrets Scanner...")

    files = get_all_files(".")
    leaks = scan_files(files)

    if Enum.empty?(leaks) do
      IO.puts("✨ Secrets Scan Passed: No leaked secrets found.")
      :ok
    else
      IO.puts("\n🔴 SECRETS SCAN FAILED: Leaked secrets detected!")

      Enum.each(leaks, fn {file, line_num, pattern_name, match} ->
        IO.puts("  - File: #{file}:#{line_num}")
        IO.puts("    Type: #{pattern_name}")

        # Redact the secret in the output for safety
        redacted = String.slice(match, 0, 8) <> "..." <> String.slice(match, -4, 4)
        IO.puts("    Match: #{redacted}")
      end)

      # Exit with error status to fail the precommit / compilation pipeline
      System.halt(1)
    end
  end

  defp get_all_files(dir) do
    case File.ls(dir) do
      {:ok, files} ->
        files
        |> Enum.flat_map(fn file ->
          path = Path.join(dir, file)
          relative_path = String.trim_leading(path, "./")

          if excluded?(relative_path) do
            []
          else
            if File.dir?(path) do
              get_all_files(path)
            else
              [relative_path]
            end
          end
        end)

      _ ->
        []
    end
  end

  defp excluded?(path) do
    Enum.any?(@excludes, &Regex.match?(&1, path))
  end

  defp scan_files(files) do
    Enum.flat_map(files, fn file ->
      case File.read(file) do
        {:ok, content} ->
          content
          |> String.split("\n")
          |> Enum.with_index(1)
          |> Enum.flat_map(fn {line, line_num} ->
            find_leaks_in_line(file, line, line_num)
          end)

        _ ->
          []
      end
    end)
  end

  defp find_leaks_in_line(file, line, line_num) do
    Enum.flat_map(@patterns, fn {name, regex} ->
      case Regex.run(regex, line) do
        [match] ->
          # Exclude placeholder test variables
          if String.contains?(match, "PLACEHOLDER") do
            []
          else
            [{file, line_num, name, match}]
          end

        _ ->
          []
      end
    end)
  end
end
