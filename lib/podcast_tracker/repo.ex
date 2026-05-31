defmodule PodcastTracker.Repo do
  use Ecto.Repo,
    otp_app: :podcast_tracker,
    adapter: Ecto.Adapters.SQLite3
end
