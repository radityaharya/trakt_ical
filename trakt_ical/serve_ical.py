"""
This file contains the code for the Flask app that serves the iCal file.
"""

import datetime
import os
import re
import tempfile
import logging

import pymongo
import requests
from cryptography.fernet import Fernet
from dotenv import load_dotenv
from flask import (
    Flask,
    Response,
    abort,
    jsonify,
    redirect,
    request,
    send_from_directory,
    url_for,
)
from flask_caching import Cache
from util import decrypt, encrypt
import sentry_sdk

from trakt_api import TraktAPI
from tmdb_api import TMDB

col = pymongo.MongoClient(os.environ.get("MONGO_URL")).trakt_ical.users

logger = logging.getLogger(__name__)

config = {
    "DEBUG": False,
    "CACHE_TYPE": "FileSystemCache",
    "CACHE_DEFAULT_TIMEOUT": 3600,
    "CACHE_DIR": "./cache",
}
app = Flask(__name__, static_folder="frontend/dist")
app.config.from_mapping(config)
cache = Cache(app)

tmdb = TMDB()

load_dotenv(override=True)

sentry_sdk.init(
    dsn=os.environ.get("SENTRY_DSN"),
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    traces_sample_rate=1.0,
    # Set profiles_sample_rate to 1.0 to profile 100%
    # of sampled transactions.
    # We recommend adjusting this value in production.
    profiles_sample_rate=1.0,
)

APPLICATION_ID = os.environ.get("TRAKT_APPLICATION_ID")
CLIENT_ID = os.environ.get("TRAKT_CLIENT_ID")
CLIENT_SECRET = os.environ.get("TRAKT_CLIENT_SECRET")

MAX_DAYS_AGO = 30
MAX_PERIOD = 90


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
        logger.info(
            {
                "message": "Token is not expired",
                "datetime": datetime.datetime.now().timestamp(),
                "info": {
                    "user_id": key,
                    "created_at": user_token["created_at"],
                    "expires_in": user_token["expires_in"],
                },
            }
        )
        return user_token
    logger.info(
        {
            "message": "Token is expired",
            "datetime": datetime.datetime.now(),
            "info": {
                "user_id": key,
                "created_at": user_token["created_at"],
                "expires_in": user_token["expires_in"],
            },
        }
    )
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
    return f"""
    <html>
    <head>
    <title>Trakt iCal</title>
    <style>
    body {{
        font-family: sans-serif;
        text-align: center;
    }}
    main {{
        width: 100%;
        height: 100%;
        display: flex;
        justify-content: center;
        align-items: center;
        display: flex;
        flex-direction: column;
    }}
    a {{
        display: inline-block;
        padding: 10px 20px;
        background-color: #2c3e50;
        color: #fff;
        text-decoration: none;
        border-radius: 5px;
    }}
    a:hover {{
        background-color: #34495e;
    }}
    </style>
    </head>
    <body>
    <main>
    <a href="https://trakt.tv/oauth/authorize?response_type=code&client_id={CLIENT_ID}&redirect_uri={os.environ.get("HOST")}/trakt/callback">Authorize with Trakt</a>
    <p> You will be redirected to Trakt.tv to authorize this app. </p>
    <p id="countdown">Redirecting in 5 seconds...</p>
    </main>
    </body>
    <script>
    function countdown() {{
        var i = 5;
        var interval = setInterval(function() {{
            i--;
            if (i == 0) {{
                clearInterval(interval);
                window.location.href = "https://trakt.tv/oauth/authorize?response_type=code&client_id={CLIENT_ID}&redirect_uri={os.environ.get("HOST")}/trakt/callback";
            }}
            document.querySelector("#countdown").innerHTML = "Redirecting in " + i + " seconds...";
        }}, 1000);
    }}
    countdown();
    </script>
    </html>
    """


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
    return redirect(url_for("index") + f"?key={key}")


@app.route("/")
def index():
    """
    This page is shown after the user has been authenticated
    """
    return send_from_directory(app.static_folder, "index.html")


@app.route("/<calendar_type>")
@cache.cached(timeout=3600, query_string=["key", "days_ago", "period"])
def calendar_ical(calendar_type):
    """
    Returns iCal file if key is provided, otherwise redirects to /auth.

    Args:
        calendar_type (str): Type of calendar (shows/movies).

    Returns:
        Response: iCal file response.
    """
    key = request.args.get("key")
    days_ago = request.args.get("days_ago")
    period = request.args.get("period")
    logger.info(
        {
            "path": request.path,
            "info": {
                "key": key,
                "days_ago": days_ago,
                "period": period,
                "calendar_type": calendar_type,
            },
        }
    )
    if calendar_type not in ["shows", "movies"]:
        return abort(404)

    if not key:
        return """
        <html>
        <head>
        <title>Trakt iCal</title>
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

    trakt_api = TraktAPI(trakt_access_token["access_token"])
    try:
        if calendar_type == "shows":
            calendar = trakt_api.get_shows_calendar(
                days_ago=days_ago,
                period=period,
            )
            filename = "trakt-calendar-shows.ics"
        elif calendar_type == "movies":
            calendar = trakt_api.get_movies_calendar(
                days_ago=days_ago,
                period=period,
            )
            filename = "trakt-calendar-movies.ics"
        else:
            return "Invalid calendar type", 400
    except ValueError as message:
        return {"error": str(message)}, 400

    with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file:
        temp_file.write(calendar)
        temp_file.flush()
        temp_file.close()

    path = os.path.join(os.path.dirname(__file__), temp_file.name)
    string = open(path, "r", encoding="utf-8").read()
    response = Response(string, mimetype="text/calendar")
    response.headers["Cache-Control"] = "max-age=3600"
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response


@app.route("/<calendar_type>/json")
@cache.cached(timeout=3600, query_string=["key", "days_ago", "period"])
def get_calendar_preview(calendar_type):
    """
    Returns a JSON response with the calendar preview.
    """
    key = request.args.get("key")
    days_ago = request.args.get("days_ago")
    period = request.args.get("period")
    logger.info(
        {
            "path": request.path,
            "info": {
                "key": key,
                "days_ago": days_ago,
                "period": period,
                "calendar_type": calendar_type,
            },
        }
    )

    if calendar_type not in ["shows", "movies"]:
        return abort(404)

    days_ago = int(days_ago) if days_ago else 30
    period = int(period) if period else 90

    if not key:
        return "No key provided", 400
    trakt_access_token = get_token(key)["access_token"]

    trakt_api = TraktAPI(trakt_access_token)

    if calendar_type == "shows":
        try:
            entries = trakt_api.get_shows_batch(days_ago, period)
        except ValueError as message:
            return {"error": str(message)}, 400
    elif calendar_type == "movies":
        try:
            entries = trakt_api.get_movies_batch(days_ago, period)
        except ValueError as message:
            return {"error": str(message)}, 400
    else:
        return "Invalid calendar type", 400

    def get_backdrop(images):
        try:
            return f"https://image.tmdb.org/t/p/w500{images.get('backdrops')[0].get('file_path')}"
        except Exception as error:
            logger.exception(
                {
                    "message": "Failed to get logo",
                    "info": {
                        "images": images,
                        "entry": entry,
                        "error": error,
                    },
                }
            )
            return None

    def get_logo(images):
        try:
            return f"https://image.tmdb.org/t/p/original{images.get('logos')[0].get('file_path')}"
        except Exception as error:
            logger.exception(
                {
                    "message": "Failed to get logo",
                    "datetime": datetime.datetime.now(),
                    "info": {
                        "images": images,
                        "entry": entry,
                        "error": error,
                    },
                }
            )
            return None

    # Separate the entries by their respective dates
    entries_by_date = {}
    for entry in entries:
        if calendar_type == "shows":
            show_ids = entry.show_data.__dict__.get("_ids")
            images = tmdb.get_show_images(show_ids.get("tmdb"))
            show_detail = tmdb.get_show(show_ids.get("tmdb"))
            entry_data = {
                "airs_at": entry.airs_at,
                "airs_at_unix": entry.airs_at.timestamp(),
                "number": entry.number,
                "overview": entry.overview,
                "runtime": entry.runtime,
                "season": entry.season,
                "show": entry.show,
                "title": entry.title,
                "background": get_backdrop(images),
                "logo": get_logo(images),
                "ids": show_ids,
                "network": show_detail.get("networks")[0].get("name"),
            }
        elif calendar_type == "movies":
            movie_ids = entry.__dict__.get("_ids")
            images = tmdb.get_movie_images(movie_ids.get("tmdb"))

            entry_data = {
                "title": entry.title,
                "overview": entry.overview,
                "released": entry.released,
                "released_unix": datetime.datetime.strptime(
                    entry.released, "%Y-%m-%d"
                ).timestamp(),
                "runtime": entry.runtime,
                "background": get_backdrop(images),
                "logo": get_logo(images),
                "ids": movie_ids,
            }

        date_unix = (
            entry_data.get("airs_at_unix")
            if calendar_type == "shows"
            else entry_data.get("released_unix")
        )

        date_unix = date_unix - (date_unix % 86400)

        date_str = datetime.datetime.utcfromtimestamp(date_unix).strftime(
            "%a, %d %b %Y %H:%M:%S GMT"
        )

        if date_unix not in entries_by_date:
            entries_by_date[date_unix] = {
                "date_unix": date_unix,
                "date_str": date_str,
                "items": [],
            }

        entries_by_date[date_unix]["items"].append(entry_data)

    # Sort the entries by their respective dates
    sorted_entries = sorted(entries_by_date.values(), key=lambda k: k["date_unix"])

    # Prepare the final response
    response_data = {
        "type": calendar_type,
        "data": sorted_entries,
    }

    response = jsonify(response_data)
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response


@app.route("/api/user/<user_id>")
def get_user(user_id):
    """
    Returns the username and slug of a user
    """
    if not user_id:
        return "No user ID provided", 400
    user = col.find_one({"user_id": user_id})
    if not user:
        return abort(404)
    else:
        trakt_access_token = get_token(user_id)["access_token"]
        username = get_user_info(trakt_access_token)["user"]["username"]
        return jsonify({"username": username, "slug": user["user_slug"]})


@app.route("/assets/<path:path>")
def send_assets(path):
    """
    Send static assets
    """
    path = path.replace("../", "")
    path = path.replace("./", "")
    path = path.replace("//", "/")
    return send_from_directory(app.static_folder, f"assets/{path}")


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
        with open(".env", "a", encoding="utf-8") as file:
            file.write(f"\nSECRET_KEY={key.decode('utf-8')}")
    app.secret_key = os.environ["SECRET_KEY"]
    app.run(host=host, port=port, debug=debug)
