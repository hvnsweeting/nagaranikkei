defmodule PodcastTracker.PodcastsTest do
  use PodcastTracker.DataCase

  alias PodcastTracker.Podcasts

  describe "episodes" do
    alias PodcastTracker.Podcasts.Episode

    import PodcastTracker.PodcastsFixtures

    @invalid_attrs %{published_at: nil, japanese_title: nil, english_translation: nil}

    test "list_episodes/0 returns all episodes" do
      episode = episode_fixture()
      assert Podcasts.list_episodes() == [episode]
    end

    test "get_episode!/1 returns the episode with given id" do
      episode = episode_fixture()
      assert Podcasts.get_episode!(episode.id) == episode
    end

    test "create_episode/1 with valid data creates a episode" do
      valid_attrs = %{
        published_at: ~N[2026-05-30 14:27:00],
        japanese_title: "some japanese_title",
        english_translation: "some english_translation",
        audio_url: "some audio_url"
      }

      assert {:ok, %Episode{} = episode} = Podcasts.create_episode(valid_attrs)
      assert episode.published_at == ~N[2026-05-30 14:27:00]
      assert episode.japanese_title == "some japanese_title"
      assert episode.english_translation == "some english_translation"
      assert episode.audio_url == "some audio_url"
    end

    test "create_episode/1 with invalid data returns error changeset" do
      assert {:error, %Ecto.Changeset{}} = Podcasts.create_episode(@invalid_attrs)
    end

    test "create_episode/1 with duplicate japanese_title returns error changeset" do
      valid_attrs = %{
        published_at: ~N[2026-05-30 14:27:00],
        japanese_title: "duplicate japanese_title",
        english_translation: "some english_translation",
        audio_url: "some audio_url"
      }

      assert {:ok, _episode} = Podcasts.create_episode(valid_attrs)
      assert {:error, %Ecto.Changeset{} = changeset} = Podcasts.create_episode(valid_attrs)
      assert %{japanese_title: ["has already been taken"]} = errors_on(changeset)
    end

    test "update_episode/2 with valid data updates the episode" do
      episode = episode_fixture()

      update_attrs = %{
        published_at: ~N[2026-05-31 14:27:00],
        japanese_title: "some updated japanese_title",
        english_translation: "some updated english_translation",
        audio_url: "some updated audio_url"
      }

      assert {:ok, %Episode{} = episode} = Podcasts.update_episode(episode, update_attrs)
      assert episode.published_at == ~N[2026-05-31 14:27:00]
      assert episode.japanese_title == "some updated japanese_title"
      assert episode.english_translation == "some updated english_translation"
      assert episode.audio_url == "some updated audio_url"
    end

    test "update_episode/2 with invalid data returns error changeset" do
      episode = episode_fixture()
      assert {:error, %Ecto.Changeset{}} = Podcasts.update_episode(episode, @invalid_attrs)
      assert episode == Podcasts.get_episode!(episode.id)
    end

    test "delete_episode/1 deletes the episode" do
      episode = episode_fixture()
      assert {:ok, %Episode{}} = Podcasts.delete_episode(episode)
      assert_raise Ecto.NoResultsError, fn -> Podcasts.get_episode!(episode.id) end
    end

    test "change_episode/1 returns a episode changeset" do
      episode = episode_fixture()
      assert %Ecto.Changeset{} = Podcasts.change_episode(episode)
    end
  end

  describe "chunks" do
    alias PodcastTracker.Podcasts.Chunk

    import PodcastTracker.PodcastsFixtures

    @invalid_attrs %{japanese_text: nil, romaji: nil, english_meaning: nil, order_index: nil}

    test "list_chunks/0 returns all chunks" do
      chunk = chunk_fixture()
      assert Podcasts.list_chunks() == [chunk]
    end

    test "get_chunk!/1 returns the chunk with given id" do
      chunk = chunk_fixture()
      assert Podcasts.get_chunk!(chunk.id) == chunk
    end

    test "create_chunk/2 with valid data creates a chunk" do
      episode = episode_fixture()

      valid_attrs = %{
        japanese_text: "some japanese_text",
        romaji: "some romaji",
        english_meaning: "some english_meaning",
        order_index: 42
      }

      assert {:ok, %Chunk{} = chunk} = Podcasts.create_chunk(episode, valid_attrs)
      assert chunk.japanese_text == "some japanese_text"
      assert chunk.romaji == "some romaji"
      assert chunk.english_meaning == "some english_meaning"
      assert chunk.order_index == 42
      assert chunk.episode_id == episode.id
    end

    test "create_chunk/2 with invalid data returns error changeset" do
      episode = episode_fixture()
      assert {:error, %Ecto.Changeset{}} = Podcasts.create_chunk(episode, @invalid_attrs)
    end

    test "update_chunk/2 with valid data updates the chunk" do
      chunk = chunk_fixture()

      update_attrs = %{
        japanese_text: "some updated japanese_text",
        romaji: "some updated romaji",
        english_meaning: "some updated english_meaning",
        order_index: 43
      }

      assert {:ok, %Chunk{} = chunk} = Podcasts.update_chunk(chunk, update_attrs)
      assert chunk.japanese_text == "some updated japanese_text"
      assert chunk.romaji == "some updated romaji"
      assert chunk.english_meaning == "some updated english_meaning"
      assert chunk.order_index == 43
    end

    test "update_chunk/2 with invalid data returns error changeset" do
      chunk = chunk_fixture()
      assert {:error, %Ecto.Changeset{}} = Podcasts.update_chunk(chunk, @invalid_attrs)
      assert chunk == Podcasts.get_chunk!(chunk.id)
    end

    test "delete_chunk/1 deletes the chunk" do
      chunk = chunk_fixture()
      assert {:ok, %Chunk{}} = Podcasts.delete_chunk(chunk)
      assert_raise Ecto.NoResultsError, fn -> Podcasts.get_chunk!(chunk.id) end
    end

    test "change_chunk/1 returns a chunk changeset" do
      chunk = chunk_fixture()
      assert %Ecto.Changeset{} = Podcasts.change_chunk(chunk)
    end
  end
end
