defmodule PodcastTracker.Repo.Migrations.AddUniqueIndexToEpisodesTitle do
  use Ecto.Migration

  def change do
    create unique_index(:episodes, [:japanese_title])
  end
end
