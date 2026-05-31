defmodule Mix.Tasks.Secrets.Scan do
  use Mix.Task

  @shortdoc "Scans the codebase for leaked secrets and API keys using Gitleaks"

  @impl Mix.Task
  def run(_args) do
    IO.puts("==> Running external Gitleaks scanner...")

    try do
      case System.cmd(
             "gitleaks",
             ["detect", "--no-git", "--source", ".", "--verbose", "--redact"],
             into: IO.stream(:stdio, :line),
             stderr_to_stdout: true
           ) do
        {_, 0} ->
          IO.puts("\n✨ Secrets Scan Passed: No leaked secrets found.")
          :ok

        {_, exit_code} ->
          IO.puts("\n🔴 SECRETS SCAN FAILED: Leaked secrets detected! (exit code #{exit_code})")
          System.halt(1)
      end
    rescue
      exception in ErlangError ->
        case exception do
          %ErlangError{original: :enoent} ->
            IO.puts("\n🔴 SECRETS SCAN ERROR: `gitleaks` binary not found in system PATH.")

            IO.puts(
              "Please install gitleaks (https://github.com/gitleaks/gitleaks) or ensure it is available in your PATH."
            )

            System.halt(1)

          _ ->
            reraise exception, __STACKTRACE__
        end
    end
  end
end
