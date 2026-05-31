defmodule PodcastTracker.Scheduler do
  use GenServer
  require Logger

  # 24 hours in milliseconds
  @interval 24 * 60 * 60 * 1000

  def start_link(_) do
    GenServer.start_link(__MODULE__, %{}, name: __MODULE__)
  end

  def init(state) do
    Logger.info("Starting PodcastTracker Scheduler...")
    # Avoid synchronous startup crash loops: delay first run by 2 seconds
    Process.send_after(self(), :work, 2000)
    {:ok, state}
  end

  def handle_info(:work, state) do
    # Execute fetch asynchronously in a spawned task so failures do not crash the GenServer
    Task.Supervisor.start_child(PodcastTracker.TaskSupervisor, fn ->
      try do
        PodcastTracker.Fetcher.run()
      rescue
        e -> Logger.error("Failed to run podcast fetcher: #{inspect(e)}")
      catch
        kind, value -> Logger.error("Failed to run podcast fetcher: #{inspect({kind, value})}")
      end
    end)

    # Schedule the next run
    Process.send_after(self(), :work, @interval)
    {:noreply, state}
  end
end
