defmodule PodcastTracker.Repo.Migrations.CreateEpisodes do
  use Ecto.Migration

  def change do
    create table(:episodes) do
      add :published_at, :naive_datetime
      add :japanese_title, :text
      add :english_translation, :text

      timestamps(type: :utc_datetime)
    end
  end
end
