import datetime
import os
import tempfile

import requests
import trakt
import trakt.core
from cryptography.fernet import Fernet
from dotenv import load_dotenv
from flask import Flask, Response, redirect, request, url_for
from flask_caching import Cache
from icalendar import Calendar, Event
import pymongo
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


def get_calendar(
    trakt_access_token: str = None,
    days_ago: int = None,
    period: int = 365,
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

    days_ago = int(days_ago) if days_ago else None

    start_date = (
        (
            (datetime.datetime.now() - datetime.timedelta(days=days_ago)).strftime(
                "%Y-%m-%d"
            )
        )
        if days_ago
        else (datetime.datetime.now() - datetime.timedelta(days=30)).strftime(
            "%Y-%m-%d"
        )
    )

    episodes = MyShowCalendar(
        days=period if period else 365,
        extended="full",
        date=start_date,
    )

    cal = Calendar()
    cal.add("prodid", "-//Trakt//trakt_ical//EN")
    cal.add("version", f"{datetime.datetime.now().strftime('%Y%m%d %H:%M')}")

    for episode in episodes:
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

    days_ago = int(days_ago) if days_ago else None

    if not key:
        return "No key provided", 400
    trakt_access_token = get_token(key)["access_token"]
    trakt.core.CLIENT_ID = CLIENT_ID
    trakt.core.CLIENT_SECRET = CLIENT_SECRET
    trakt.core.OAUTH_TOKEN = trakt_access_token

    start_date = (
        (
            (datetime.datetime.now() - datetime.timedelta(days=days_ago)).strftime(
                "%Y-%m-%d"
            )
        )
        if days_ago
        else (datetime.datetime.now() - datetime.timedelta(days=30)).strftime(
            "%Y-%m-%d"
        )
    )

    print(start_date)
    episodes = MyShowCalendar(
        days=period if period else 365,
        extended="full",
        date=start_date,
    )

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
            }
        )
    return json


def get_token(key: str):
    """
    Returns the token for the user with the given key
    """
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


@app.route("/complete")
@cache.cached(timeout=3600, query_string=True)
def complete():
    """
    This page is shown after the user has been authenticated
    """
    key = request.args.get("key")
    if not key:
        return redirect(url_for("authorize"))
    trakt_access_token = get_token(key)["access_token"]
    username = get_user_info(trakt_access_token)["user"]["username"]

    page = f"""
    <html>
    <head>
    <title>Trakt ical</title>
    <style>
    table, th, td {{
        border: 1px solid;
    }}

    th, td{{
        padding: 5px
    }}
    </style>
    </head>
    <body>
    <h1 style="margin-bottom: 5px;">Trakt ICal Feed</h1>
    <a href="https://github.com/radityaharya/trakt_ical" target="_blank" style="text-decoration: none; color: blue;">Github</a>
    <br>
    <p>Authenticated as <strong>{username}</strong></p>
    <div>
        <label for="days_from">Days Ago:</label>
        <input type="number" id="days_ago" value="1" onchange="actions()">
        <label for="days">Days Ahead:</label>
        <input type="number" id="days" value="32" max="365" min="30" onchange="actions()">
        <button onclick="actions()">Update url</button>
    </div>
    <p style="font-size: 12px;" id="estimated_time"></p>
    <p style="font-size: 12px;">Note: The current maximum time span that can be fetched is 33 days</p>
    <p>Now you can use the following link to get your ical file:</p>
    <p id="url"><a href="{url_for('index')}?key={key}">{url_for('index')}?key={key}</a></p>
    <button onclick="copyUrl()">Copy url</button>
    <button onclick="addGoogle()">Add to Google Calendar</button>
    <button onclick="addOutlook365()">Add to Outlook 365</button>
    <button onclick="addOutlookLive()">Add to Outlook Live</button>
    <h2>Add to Google Calendar</h2>
    <p>1. Go to <a target="_blank"href="https://calendar.google.com/calendar/r/settings/addbyurl">https://calendar.google.com/calendar/r/settings/addbyurl</a></p>
    <p>2. Paste the following link into the field and click "Add calendar"</p>
    <p> or click the following button to add the calendar directly to your Google Calendar</p>
    
    <button onclick="addGoogle()">Add to Google Calendar</button>
    
    <h2>Add to Outlook</h2>
    <p>1. Go to <a target="_blank" href="https://outlook.live.com/calendar/0/subscriptions">https://outlook.live.com/calendar/0/subscriptions</a></p>
    <p>2. Paste the following link into the field and click "Add"</p>
    
    <p> or click the following button to add the calendar directly to your Outlook</p>
    
    <button onclick="addOutlook365()">Add to Outlook 365</button>
    <button onclick="addOutlookLive()">Add to Outlook Live</button>
    
    <p>Preview:</p>
    <div id="preview"></div>
    <noscript>
        <p style="color: red;">Javascript is required to render the preview table</p>
    </noscript>
    
    </body>
    <script type="text/javascript" src="/static/js/script.js"></script>
    </html>
    """
    return page


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
    period = int(period) if period else None

    try:
        col.find_one({"user_id": key})
    except Exception:
        return redirect(url_for("authorize"))
    trakt_access_token = get_token(key)

    calendar = get_calendar(
        trakt_access_token=trakt_access_token["access_token"],
        days_ago=days_ago,
        period=period,
    )

    with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file:
        temp_file.write(calendar)
        temp_file.flush()
        temp_file.close()

    path = os.path.join(os.path.dirname(__file__), temp_file.name)

    response = Response(open(path, "rb"), mimetype="text/calendar")
    response.headers["Cache-Control"] = "max-age=3600"
    response.headers["Content-Disposition"] = f"attachment; filename=trakt-calendar.ics"
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
