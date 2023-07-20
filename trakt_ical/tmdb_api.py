import os
import requests


class TMDB:
    def __init__(self):
        self.access_token = os.getenv("TMDB_ACCESS_TOKEN")
        self.base_url = "https://api.themoviedb.org/3"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}",
        }

    def _req(self, method: str, url: str, **kwargs):
        return requests.request(method, url, headers=self.headers, **kwargs, timeout=10)

    def get_show_images(self, show_id: int):
        url = f"{self.base_url}/tv/{show_id}/images"
        return self._req("GET", url).json()

    def get_movie_images(self, movie_id: int):
        url = f"{self.base_url}/movie/{movie_id}/images"
        return self._req("GET", url).json()

    def get_movie(self, movie_id: int):
        url = f"{self.base_url}/movie/{movie_id}"
        return self._req("GET", url).json()

    def get_show(self, show_id: int):
        url = f"{self.base_url}/tv/{show_id}"
        return self._req("GET", url).json()
