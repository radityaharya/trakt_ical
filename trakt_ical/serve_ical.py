import datetime
import os

import requests
import trakt
import trakt.core
from cryptography.fernet import Fernet
from dotenv import load_dotenv
from flask import Flask, Response, redirect, request, url_for
from flask_caching import Cache
from icalendar import Calendar, Event
from montydb import MontyClient, set_storage
from trakt.calendar import MyShowCalendar
from util import decrypt, encrypt

set_storage("./data", use_bson=True, mongo_version="4.0")
col = MontyClient("./data").db.users

config = {"DEBUG": False, "CACHE_TYPE": "SimpleCache", "CACHE_DEFAULT_TIMEOUT": 3600}
app = Flask(__name__)
app.config.from_mapping(config)
cache = Cache(app)


load_dotenv(override=True)

APPLICATION_ID = os.environ.get("TRAKT_APPLICATION_ID")
CLIENT_ID = os.environ.get("TRAKT_CLIENT_ID")
CLIENT_SECRET = os.environ.get("TRAKT_CLIENT_SECRET")


def get_calendar(trakt_access_token: str = None) -> str:
    """
    Returns the calendar in iCal format for the next 365 days encoded in utf-8

    Returns:
        str: iCal calendar
    """
    trakt.core.CLIENT_ID = CLIENT_ID
    trakt.core.CLIENT_SECRET = CLIENT_SECRET
    trakt.core.OAUTH_TOKEN = trakt_access_token

    episodes = MyShowCalendar(
        days=365,
        extended="full",
        date=(datetime.datetime.now() - datetime.timedelta(days=30)).strftime(
            "%Y-%m-%d"
        ),
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


def get_token(key: str):
    user_token = col.find_one({"user_id": key})["token"]
    user_token = decrypt(user_token)
    # check if the token is expired
    if (
        datetime.datetime.now().timestamp()
        < user_token["created_at"] + user_token["expires_in"]
    ):
        print("Token is not expired")
        return user_token
    # refresh the token if it is expired
    print("Refreshing token")
    data = {
        "refresh_token": user_token["refresh_token"],
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token",
        "redirect_uri": os.environ.get("HOST") + "/trakt/callback",
    }
    response = requests.post("https://trakt.tv/oauth/token", data=data)
    print(response.json())
    user_slug = get_user_info(response.json()["access_token"])["user"]["ids"]["slug"]
    col.update_one(
        {"user_slug": user_slug}, {"$set": {"token": encrypt(response.json())}}
    )
    return response.json()


def get_user_info(trakt_access_token: str = None):
    url = "https://api.trakt.tv/users/settings"
    headers = {
        "Content-Type": "application/json",
        "trakt-api-version": "2",
        "trakt-api-key": CLIENT_ID,
        "Authorization": f"Bearer {trakt_access_token}",
    }
    response = requests.get(url, headers=headers)
    return response.json()


@app.route("/auth")
def authorize():
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
    key = os.urandom(20).hex()
    code = request.args.get("code")
    data = {
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "redirect_uri": os.environ.get("HOST") + "/trakt/callback",
    }
    response = requests.post("https://trakt.tv/oauth/token", data=data)
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
    trakt_user = col.find_one({"user_id": key})
    trakt_access_token = get_token(key)["access_token"]
    username = get_user_info(trakt_access_token)["user"]["username"]
    page = f"""
    <html>
    <head>
    <title>Trakt ical</title>
    </head>
    <body>
    <h1>Authentication successful</h1>
    <p>Auhtenticated as <b>{username}</b></p>
    <p>Now you can use the following link to get your ical file:</p>
    <p id="url"><a href="{url_for('index')}?key={key}">{url_for('index')}?key={key}</a></p>
    <button onclick="copyUrl()">Copy url</button>
    <h2>Add to Google Calendar</h2>
    <p>1. Go to <a target="_blank"href="https://calendar.google.com/calendar/r/settings/addbyurl">https://calendar.google.com/calendar/r/settings/addbyurl</a></p>
    <p>2. Paste the following link into the field and click "Add calendar"</p>
    
    <h2>Add to Outlook</h2>
    <p>1. Go to <a target="_blank" href="https://outlook.live.com/calendar/0/subscriptions">https://outlook.live.com/calendar/0/subscriptions</a></p>
    <p>2. Paste the following link into the field and click "Add"</p>

    
    
    </body>
    <script>
    function editUrl() {{
        //get base url
        var url = window.location.href;
        var base_url = url.substring(0, url.lastIndexOf("/"));
        //get key
        var key = document.getElementById("url").innerText.split("?key=")[1];
        //set new url
        document.getElementById("url").innerHTML = `<a href="${{base_url}}/?key=${{key}}">${{base_url}}/?key=${{key}}</a>`;      
    }}
    
    function copyUrl() {{
        var url = document.getElementById("url").innerText;
        navigator.clipboard.writeText(url);
    }}
    
    editUrl();
    </script>
    </html>
    """
    return page


@app.route("/")
@cache.cached(timeout=3600, query_string=True)
def index():
    """
    Returns ical file if key is provided, otherwise redirects to /auth
    """
    key = request.args.get("key")
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
    try:
        col.find_one({"user_id": key})
    except:
        return redirect(url_for("authorize"))
    trakt_access_token = get_token(key)
    return Response(
        get_calendar(trakt_access_token=trakt_access_token["access_token"]),
        mimetype="text/calendar",
    )


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
        with open(".env", "a") as f:
            f.write(f"\nSECRET_KEY={key.decode('utf-8')}")
    app.secret_key = os.environ["SECRET_KEY"]
    app.run(host=host, port=port, debug=debug)
