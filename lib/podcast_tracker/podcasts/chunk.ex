defmodule PodcastTracker.Podcasts.Chunk do
  use Ecto.Schema
  import Ecto.Changeset

  schema "chunks" do
    field :japanese_text, :string
    field :romaji, :string
    field :english_meaning, :string
    field :order_index, :integer
    belongs_to :episode, PodcastTracker.Podcasts.Episode

    timestamps(type: :utc_datetime)
  end

  def changeset(chunk, attrs) do
    chunk
    |> cast(attrs, [:japanese_text, :romaji, :english_meaning, :order_index])
    |> validate_required([:japanese_text, :romaji, :english_meaning, :order_index])
  end
end
