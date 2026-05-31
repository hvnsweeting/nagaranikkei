defmodule PodcastTracker.Podcasts.Episode do
  use Ecto.Schema
  import Ecto.Changeset

  schema "episodes" do
    field :published_at, :naive_datetime
    field :japanese_title, :string
    field :english_translation, :string
    field :audio_url, :string
    has_many :chunks, PodcastTracker.Podcasts.Chunk

    timestamps(type: :utc_datetime)
  end

  @doc false
  def changeset(episode, attrs) do
    episode
    |> cast(attrs, [:published_at, :japanese_title, :english_translation, :audio_url])
    |> validate_required([:published_at, :japanese_title, :english_translation])
    |> unique_constraint(:japanese_title)
  end
end
