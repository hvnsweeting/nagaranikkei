defmodule PodcastTracker.PodcastsFixtures do
  @moduledoc """
  This module defines test helpers for creating
  entities via the `PodcastTracker.Podcasts` context.
  """

  @doc """
  Generate a episode.
  """
  def episode_fixture(attrs \\ %{}) do
    {:ok, episode} =
      attrs
      |> Enum.into(%{
        english_translation: "some english_translation",
        japanese_title: "some japanese_title",
        published_at: ~N[2026-05-30 14:27:00],
        audio_url: "some audio_url"
      })
      |> PodcastTracker.Podcasts.create_episode()

    episode
  end

  @doc """
  Generate a chunk.
  """
  def chunk_fixture(attrs \\ %{}) do
    attrs = Map.new(attrs)

    episode =
      case Map.get(attrs, :episode) do
        nil ->
          episode_id = Map.get(attrs, :episode_id) || Map.get(attrs, "episode_id")

          if episode_id do
            PodcastTracker.Podcasts.get_episode!(episode_id)
          else
            episode_fixture()
          end

        ep ->
          ep
      end

    attrs =
      attrs
      |> Map.delete(:episode)
      |> Map.delete(:episode_id)
      |> Map.delete("episode_id")

    {:ok, chunk} =
      attrs
      |> Enum.into(%{
        english_meaning: "some english_meaning",
        japanese_text: "some japanese_text",
        order_index: 42,
        romaji: "some romaji"
      })
      |> then(&PodcastTracker.Podcasts.create_chunk(episode, &1))

    chunk
  end
end
