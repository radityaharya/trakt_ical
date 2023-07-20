"""
Module for interacting with the Trakt API
"""

import concurrent.futures
import datetime
import os

import trakt
import trakt.core
from icalendar import Calendar, Event
from trakt.calendar import MyMovieCalendar, MyShowCalendar
from tmdb_api import TMDB

APPLICATION_ID = os.environ.get("TRAKT_APPLICATION_ID")
CLIENT_ID = os.environ.get("TRAKT_CLIENT_ID")
CLIENT_SECRET = os.environ.get("TRAKT_CLIENT_SECRET")

MAX_DAYS_AGO = 30
MAX_PERIOD = 90


class TraktAPI:
    """
    Class for interacting with the Trakt API
    """

    def __init__(self, oauth_token=None):
        self.client_id = os.environ.get("TRAKT_CLIENT_ID")
        self.client_secret = os.environ.get("TRAKT_CLIENT_SECRET")
        self.oauth_token = oauth_token
        trakt.core.CLIENT_ID = self.client_id
        trakt.core.CLIENT_SECRET = self.client_secret
        if oauth_token:
            trakt.core.OAUTH_TOKEN = oauth_token
        self.tmdb = TMDB()

    def get_shows_batch(self, days_ago: int, period: int):
        """
        Returns the episodes for the given start date and days
        """
        episodes = []
        if days_ago > MAX_DAYS_AGO or period > MAX_PERIOD:
            raise ValueError(
                f"days_ago must be less than {MAX_DAYS_AGO} and period must be less than {MAX_PERIOD}"
            )

        def get_episodes(start_date, days):
            print(start_date, days)
            return MyShowCalendar(
                days=days,
                extended="full",
                date=start_date,
            )

        start_date = (
            datetime.datetime.now() - datetime.timedelta(days=days_ago)
        ).strftime("%Y-%m-%d")
        end_date = (datetime.datetime.now() + datetime.timedelta(days=period)).strftime(
            "%Y-%m-%d"
        )

        if (
            datetime.datetime.strptime(end_date, "%Y-%m-%d")
            - datetime.datetime.strptime(start_date, "%Y-%m-%d")
        ).days < 33:
            episodes = get_episodes(start_date, period)
        else:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = []
                batch_start_date = start_date
                while (
                    datetime.datetime.strptime(end_date, "%Y-%m-%d")
                    - datetime.datetime.strptime(batch_start_date, "%Y-%m-%d")
                ).days > 33:
                    futures.append(executor.submit(get_episodes, batch_start_date, 33))
                    batch_start_date = (
                        datetime.datetime.strptime(batch_start_date, "%Y-%m-%d")
                        + datetime.timedelta(days=33)
                    ).strftime("%Y-%m-%d")
                futures.append(
                    executor.submit(
                        get_episodes,
                        batch_start_date,
                        (
                            datetime.datetime.strptime(end_date, "%Y-%m-%d")
                            - datetime.datetime.strptime(batch_start_date, "%Y-%m-%d")
                        ).days,
                    )
                )
                for future in concurrent.futures.as_completed(futures):
                    episodes += future.result()
        return episodes

    def get_movies_batch(self, days_ago: int, period: int):
        """
        Returns the movies for the given start date and days
        """
        movies = []
        if days_ago > MAX_DAYS_AGO or period > MAX_PERIOD:
            raise ValueError(
                f"days_ago must be less than {MAX_DAYS_AGO} and period must be less than {MAX_PERIOD}"
            )

        def get_movies(start_date, days):
            print(start_date, days)
            return MyMovieCalendar(
                days=days,
                extended="full",
                date=start_date,
            )

        start_date = (
            datetime.datetime.now() - datetime.timedelta(days=days_ago)
        ).strftime("%Y-%m-%d")
        end_date = (datetime.datetime.now() + datetime.timedelta(days=period)).strftime(
            "%Y-%m-%d"
        )

        if (
            datetime.datetime.strptime(end_date, "%Y-%m-%d")
            - datetime.datetime.strptime(start_date, "%Y-%m-%d")
        ).days < 33:
            movies = get_movies(start_date, period)
        else:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = []
                batch_start_date = start_date
                while (
                    datetime.datetime.strptime(end_date, "%Y-%m-%d")
                    - datetime.datetime.strptime(batch_start_date, "%Y-%m-%d")
                ).days > 33:
                    futures.append(executor.submit(get_movies, batch_start_date, 33))
                    batch_start_date = (
                        datetime.datetime.strptime(batch_start_date, "%Y-%m-%d")
                        + datetime.timedelta(days=33)
                    ).strftime("%Y-%m-%d")
                futures.append(
                    executor.submit(
                        get_movies,
                        batch_start_date,
                        (
                            datetime.datetime.strptime(end_date, "%Y-%m-%d")
                            - datetime.datetime.strptime(batch_start_date, "%Y-%m-%d")
                        ).days,
                    )
                )
                for future in concurrent.futures.as_completed(futures):
                    movies += future.result()
        return movies

    def get_shows_calendar(
        self,
        days_ago: int = 30,
        period: int = 90,
    ):
        """
        Returns the calendar in iCal format for the next

        Returns:
            str: iCal calendar
            days_ago (int): days ago to start the calendar. Defaults to None.
            period (int, optional): The number of days to include in the calendar. Defaults to 365.
        """

        days_ago = int(days_ago) if days_ago else 30
        period = int(period) if period else 90

        episodes = self.get_shows_batch(days_ago, period)

        cal = Calendar()
        cal.add("prodid", "-//Trakt//trakt_ical//EN")
        cal.add("version", f"{datetime.datetime.now().strftime('%Y%m%d %H:%M')}")

        for episode in episodes:
            if episode.runtime is None or episode.runtime == 0:
                episode.runtime = 30
            show_ids = episode.show_data.__dict__.get("_ids")
            show_detail = self.tmdb.get_show(show_ids.get("tmdb"))
            summary = f"{episode.show} - S{episode.season:02d}E{episode.number:02d}"
            event = Event()
            event.add("summary", summary)
            event.add("dtstart", episode.airs_at)
            event.add(
                "dtend",
                episode.airs_at + datetime.timedelta(minutes=episode.show_data.runtime),
            )
            event.add("dtstamp", datetime.datetime.now())
            event.add("uid", f"{episode.show}-{episode.season}-{episode.number}")
            overview = episode.overview
            if overview:
                event.add("description", episode.title + "\n" + overview)
            else:
                event.add("description", episode.title)
            if show_detail.get("networks")[0].get("name"):
                event.add("location", show_detail.get("networks")[0].get("name"))
            cal.add_component(event)
        return cal.to_ical().decode("utf-8")

    def get_movies_calendar(
        self,
        days_ago: int = 30,
        period: int = 90,
    ):
        """
        Returns the calendar in iCal format for the next 365 days encoded in utf-8

        Returns:
            str: iCal calendar
            days_ago (int): days ago to start the calendar. Defaults to None.
            period (int, optional): The number of days to include in the calendar. Defaults to 365.
        """

        days_ago = int(days_ago) if days_ago else 30
        period = int(period) if period else 90

        movies = self.get_movies_batch(days_ago, period)

        cal = Calendar()
        cal.add("prodid", "-//Trakt//trakt_ical//EN")
        cal.add("version", f"{datetime.datetime.now().strftime('%Y%m%d %H:%M')}")

        for movie in movies:
            year = datetime.datetime.strptime(movie.released, "%Y-%m-%d").year
            summary = f"{movie.title} ({year})"
            event = Event()
            event.add("summary", summary)
            event.add("dtstart", datetime.datetime.strptime(movie.released, "%Y-%m-%d"))
            event.add(
                "dtend",
                datetime.datetime.strptime(movie.released, "%Y-%m-%d")
                + datetime.timedelta(hours=2),
            )
            event.add("dtstamp", datetime.datetime.now())
            event.add("uid", f"{movie.title}-{movie.released}")
            overview = movie.overview
            if overview:
                event.add("description", overview)
            else:
                event.add("description", movie.title)
            cal.add_component(event)
        return cal.to_ical().decode("utf-8")
