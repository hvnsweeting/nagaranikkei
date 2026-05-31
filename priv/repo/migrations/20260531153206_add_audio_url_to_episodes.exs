defmodule PodcastTracker.Repo.Migrations.AddAudioUrlToEpisodes do
  use Ecto.Migration

  def change do
    alter table(:episodes) do
      add :audio_url, :string
    end
  end
end
