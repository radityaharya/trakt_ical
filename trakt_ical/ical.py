import datetime
import os

import trakt
import trakt.core
from trakt.calendar import MyShowCalendar
from trakt.users import User
from icalendar import Calendar, Event
from dotenv import load_dotenv

load_dotenv(override=True)
if not os.path.exists("./trakt_config.json"):
    trakt.core.CLIENT_ID = os.environ.get("TRAKT_CLIENT_ID")
    trakt.core.CLIENT_SECRET = os.environ.get("TRAKT_CLIENT_SECRET")
    trakt.core.OAUTH_TOKEN = os.environ.get("TRAKT_OAUTH_TOKEN")
else:
    trakt.core.CONFIG_PATH = "./trakt_config.json"
try:
    me = User("otied")
except Exception as e:
    print(e)

ICAL_PATH = "./trakt.ics"


def main():
    """
    > It takes the next 365 days of episodes from your Trakt calendar, and creates an iCal file with
    them
    """
    episodes = MyShowCalendar(
        days=365, extended="full", date=(datetime.datetime.now() - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
    )

    cal = Calendar()
    cal.add("prodid", "-//Trakt//trakt_ical//EN")
    cal.add("version", f"{datetime.datetime.now().strftime('%Y%m%d %H:%M')}")

    for episode in episodes:
        print(episode.show + " - " + f"S{episode.season:02d}E{episode.number:02d}")
        summary = f"{episode.show} S{episode.season:02d}E{episode.number:02d}"
        event = Event()
        event.add("summary", summary)
        event.add("dtstart", episode.airs_at)
        event.add("dtend", episode.airs_at + datetime.timedelta(minutes=30))
        event.add("dtstamp", datetime.datetime.now())
        event.add("uid", f"{episode.show}-{episode.season}-{episode.number}")
        overview = episode.overview
        if overview:
            event.add("description", episode.title + "\n" + overview)
        else:
            event.add("description", episode.title)
        cal.add_component(event)
    return cal.to_ical().decode("utf-8")