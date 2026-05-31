defmodule PodcastTracker.Repo.Migrations.CreateChunks do
  use Ecto.Migration

  def change do
    create table(:chunks) do
      add :japanese_text, :text
      add :romaji, :text
      add :english_meaning, :text
      add :order_index, :integer
      add :episode_id, references(:episodes, on_delete: :nothing)

      timestamps(type: :utc_datetime)
    end

    create index(:chunks, [:episode_id])
  end
end
