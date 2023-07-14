import concurrent.futures
import datetime
import os
import re
import tempfile

import pymongo
import requests
import trakt
import trakt.core
from cryptography.fernet import Fernet
from dotenv import load_dotenv
from flask import Flask, Response, redirect, request, url_for, render_template
from flask_caching import Cache
from icalendar import Calendar, Event
from trakt.calendar import MyShowCalendar
from util import decrypt, encrypt

col = pymongo.MongoClient(os.environ.get("MONGO_URL")).trakt_ical.users

config = {"DEBUG": False, "CACHE_TYPE": "SimpleCache", "CACHE_DEFAULT_TIMEOUT": 3600}
app = Flask(__name__)
app.config.from_mapping(config)
cache = Cache(app)


load_dotenv(override=True)

APPLICATION_ID = os.environ.get("TRAKT_APPLICATION_ID")
CLIENT_ID = os.environ.get("TRAKT_CLIENT_ID")
CLIENT_SECRET = os.environ.get("TRAKT_CLIENT_SECRET")

MAX_DAYS_AGO = 30
MAX_PERIOD = 90


def get_episodes_batch(days_ago, period):
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

    start_date = (datetime.datetime.now() - datetime.timedelta(days=days_ago)).strftime(
        "%Y-%m-%d"
    )
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


def get_calendar(
    trakt_access_token: str = None,
    days_ago: int = 30,
    period: int = 30,
):
    """
    Returns the calendar in iCal format for the next 365 days encoded in utf-8

    Returns:
        str: iCal calendar
        days_ago (int): days ago to start the calendar. Defaults to None.
        period (int, optional): The number of days to include in the calendar. Defaults to 365.
    """
    trakt.core.CLIENT_ID = CLIENT_ID
    trakt.core.CLIENT_SECRET = CLIENT_SECRET
    trakt.core.OAUTH_TOKEN = trakt_access_token

    days_ago = int(days_ago) if days_ago else 30
    period = int(period) if period else 90

    episodes = get_episodes_batch(days_ago, period)

    cal = Calendar()
    cal.add("prodid", "-//Trakt//trakt_ical//EN")
    cal.add("version", f"{datetime.datetime.now().strftime('%Y%m%d %H:%M')}")

    for episode in episodes:
        summary = f"{episode.show} S{episode.season:02d}E{episode.number:02d}"
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
        cal.add_component(event)
    return cal.to_ical().decode("utf-8")


@cache.cached(timeout=3600, query_string=["key", "days_ago", "period"])
@app.route("/preview")
def get_calendar_preview():
    """
    Returns the calendar in iCal format for the next 365 days encoded in utf-8

    Returns:
        str: iCal calendar
        start_date (datetime.datetime, optional): The start date of the calendar. Defaults to None.
        period (int, optional): The number of days to include in the calendar. Defaults to 365.
    """
    key = request.args.get("key")
    days_ago = request.args.get("days_ago")
    period = request.args.get("period")

    days_ago = int(days_ago) if days_ago else 30
    period = int(period) if period else 90

    if not key:
        return "No key provided", 400
    trakt_access_token = get_token(key)["access_token"]
    trakt.core.CLIENT_ID = CLIENT_ID
    trakt.core.CLIENT_SECRET = CLIENT_SECRET
    trakt.core.OAUTH_TOKEN = trakt_access_token

    try:
        episodes = get_episodes_batch(days_ago, period)
    except ValueError as e:
        return {"error": str(e)}, 400
    json = []

    for episode in episodes:
        json.append(
            {
                "show": episode.show,
                "season": episode.season,
                "number": episode.number,
                "title": episode.title,
                "overview": episode.overview,
                "airs_at": episode.airs_at,
                "airs_at_unix": episode.airs_at.timestamp(),
                "runtime": episode.show_data.runtime,
            }
        )
    json = sorted(json, key=lambda k: k["airs_at_unix"])
    return json


def get_token(key: str):
    """
    Returns the token for the user with the given key
    """
    key = re.sub(r"[^a-zA-Z0-9]", "", key)
    user_token = col.find_one({"user_id": key})["token"]
    user_token = decrypt(user_token)
    if (
        datetime.datetime.now().timestamp()
        < user_token["created_at"] + user_token["expires_in"]
    ):
        print("Token is not expired")
        return user_token
    print("Refreshing token")
    data = {
        "refresh_token": user_token["refresh_token"],
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token",
        "redirect_uri": os.environ.get("HOST") + "/trakt/callback",
    }
    response = requests.post("https://trakt.tv/oauth/token", data=data, timeout=5)
    user_slug = get_user_info(response.json()["access_token"])["user"]["ids"]["slug"]
    col.update_one(
        {"user_slug": user_slug}, {"$set": {"token": encrypt(response.json())}}
    )
    return response.json()


def get_user_info(trakt_access_token: str = None):
    """
    Returns the user info for the given access token
    """
    url = "https://api.trakt.tv/users/settings"
    headers = {
        "Content-Type": "application/json",
        "trakt-api-version": "2",
        "trakt-api-key": CLIENT_ID,
        "Authorization": f"Bearer {trakt_access_token}",
    }
    response = requests.get(url, headers=headers, timeout=5)
    return response.json()


@app.route("/auth")
def authorize():
    """
    Redirects the user to the Trakt authorization page
    """
    return redirect(
        f'https://trakt.tv/oauth/authorize?response_type=code&client_id={CLIENT_ID}&redirect_uri={os.environ.get("HOST")}/trakt/callback'
    )


@app.route("/trakt/callback")
def callback():
    """
    We get the code from the URL, send a POST request to the Trakt API to get the access token,
    assigns a random key to the user, and stores an encrypted version of the token in the database
    if the user is not already in the database otherwise it updates the token
    """
    code = request.args.get("code")
    data = {
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "redirect_uri": os.environ.get("HOST") + "/trakt/callback",
    }
    response = requests.post("https://trakt.tv/oauth/token", data=data, timeout=5)
    user_slug = get_user_info(response.json()["access_token"])["user"]["ids"]["slug"]
    if not col.find_one({"user_slug": user_slug}):
        key = os.urandom(20).hex()
        col.insert_one(
            {"user_id": key, "user_slug": user_slug, "token": encrypt(response.json())}
        )
    else:
        key = col.find_one({"user_slug": user_slug})["user_id"]
    return redirect(url_for("complete", key=key))


@cache.cached(timeout=3600, query_string=True)
@app.route("/complete")
def complete():
    """
    This page is shown after the user has been authenticated
    """
    key = request.args.get("key")
    if not key:
        return redirect(url_for("authorize"))
    trakt_access_token = get_token(key)["access_token"]
    username = get_user_info(trakt_access_token)["user"]["username"]
    return render_template("complete.jinja2", username=username, key=key)


@cache.cached(timeout=3600, query_string=["key", "days_ago", "period"])
@app.route("/")
def index():
    """
    Returns ical file if key is provided, otherwise redirects to /auth
    """
    key = request.args.get("key")
    days_ago = request.args.get("days_ago")
    period = request.args.get("period")
    if not key:
        return """
        <html>
        <head>
        <title>Trakt ical</title>
        <script>
        function redirect() {
            setTimeout(function(){ window.location.href = "/auth"; }, 5000);
        }
        redirect();
        </script>
        </head>
        <body>
        No key provided, redirecting to <a href="/auth">/auth</a> in 5 seconds
        </body>
        </html>
    """
    period = int(period) if period else 90

    user = col.find_one({"user_id": key})
    if not user:
        return redirect(url_for("authorize"))
    trakt_access_token = get_token(key)

    try:
        calendar = get_calendar(
            trakt_access_token=trakt_access_token["access_token"],
            days_ago=days_ago,
            period=period,
        )
    except ValueError as e:
        return {"error": str(e)}, 400

    with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file:
        temp_file.write(calendar)
        temp_file.flush()
        temp_file.close()

    path = os.path.join(os.path.dirname(__file__), temp_file.name)

    response = Response(open(path, "rb"), mimetype="text/calendar")
    response.headers["Cache-Control"] = "max-age=3600"
    response.headers["Content-Disposition"] = "attachment; filename=trakt-calendar.ics"
    return response


def serve(host: str = "0.0.0.0", port: int = 8000, debug: bool = False):
    """
    Run the app

    :param host: Host to run the app on
    :param port: Port to run the app on
    :param debug: Enable debug mode
    """
    if "SECRET_KEY" not in os.environ:
        key = Fernet.generate_key()
        os.environ["SECRET_KEY"] = key.decode("utf-8")
        with open(".env", "a", encoding="utf-8") as f:
            f.write(f"\nSECRET_KEY={key.decode('utf-8')}")
    app.secret_key = os.environ["SECRET_KEY"]
    app.run(host=host, port=port, debug=debug)
