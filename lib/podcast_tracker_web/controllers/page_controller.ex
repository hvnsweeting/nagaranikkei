defmodule PodcastTrackerWeb.PageController do
  use PodcastTrackerWeb, :controller
  alias PodcastTracker.Podcasts

  def home(conn, _params) do
    episodes = Podcasts.list_episodes_with_chunks()
    render(conn, :home, layout: false, episodes: episodes)
  end
end
