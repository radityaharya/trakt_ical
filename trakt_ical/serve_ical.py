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
    start_date: datetime.datetime = None,
    period: int = 365,
):
    """
    Returns the calendar in iCal format for the next 365 days encoded in utf-8

    Returns:
        str: iCal calendar
        start_date (datetime.datetime, optional): The start date of the calendar. Defaults to None.
        period (int, optional): The number of days to include in the calendar. Defaults to 365.
    """
    trakt.core.CLIENT_ID = CLIENT_ID
    trakt.core.CLIENT_SECRET = CLIENT_SECRET
    trakt.core.OAUTH_TOKEN = trakt_access_token

    start_date = (
        start_date.strftime("%Y-%m-%d")
        if start_date
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


@cache.cached(timeout=3600, query_string=["key", "start_date", "period"])
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
    start_date = request.args.get("start_date")
    period = request.args.get("period")

    if not key:
        return "No key provided", 400
    trakt_access_token = get_token(key)["access_token"]
    trakt.core.CLIENT_ID = CLIENT_ID
    trakt.core.CLIENT_SECRET = CLIENT_SECRET
    trakt.core.OAUTH_TOKEN = trakt_access_token

    start_date = (
        start_date
        if start_date
        else (datetime.datetime.now() - datetime.timedelta(days=30)).strftime(
            "%Y-%m-%d"
        )
    )

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
    <p>Authenticated as {username}</p>
    <div>
        <label for="date">Start date:</label>
        <input type="date" id="date" value="{(datetime.datetime.now() - datetime.timedelta(days=10)).strftime("%Y-%m-%d")}" onchange="editUrl()">
        <label for="days">Days:</label>
        <input type="number" id="days" value="365" max="365" min="30" onchange="editUrl()">
        <button onclick="editUrl()">Update url</button>
    </div>
    <p>Now you can use the following link to get your ical file:</p>
    <p id="url"><a href="{url_for('index')}?key={key}">{url_for('index')}?key={key}</a></p>
    <button onclick="copyUrl()">Copy url</button>
    <h2>Add to Google Calendar</h2>
    <p>1. Go to <a target="_blank"href="https://calendar.google.com/calendar/r/settings/addbyurl">https://calendar.google.com/calendar/r/settings/addbyurl</a></p>
    <p>2. Paste the following link into the field and click "Add calendar"</p>
    
    <h2>Add to Outlook</h2>
    <p>1. Go to <a target="_blank" href="https://outlook.live.com/calendar/0/subscriptions">https://outlook.live.com/calendar/0/subscriptions</a></p>
    <p>2. Paste the following link into the field and click "Add"</p>
    
    <p>Preview:</p>
    <div id="preview"></div>
    <noscript>
        <p style="color: red;">Javascript is required to render the preview table</p>
    </noscript>
    
    </body>
    <script>
    function editUrl() {{
        const url = window.location.href;
        var base_url = url.substring(0, url.lastIndexOf("/"));
        var key = url.substring(url.lastIndexOf("=") + 1);
        
        var date = document.getElementById("date").value;
        var days = document.getElementById("days").value;
                
        var newurl = new URL(base_url);
        newurl = newurl.toString();
        newurl = newurl.split("?")[0];
        
        var params = new URLSearchParams();
        
        params.append("key", key);
        params.append("start_date", date);
        params.append("period", days);
        
        const final_url = `${{newurl}}?${{params.toString()}}`;
        
        document.getElementById("url").innerHTML = `<a href="${{final_url}}">${{final_url}}</a>`;
        renderPreviewTable()
    }}
    
    function copyUrl() {{
        var url = document.getElementById("url").innerText;
        navigator.clipboard.writeText(url);
    }}
    
    async function renderPreviewTable(){{
        var table = document.getElementById("preview");
        
        const url = window.location.href;
        var base_url = url.substring(0, url.lastIndexOf("/"));
        var key = url.substring(url.lastIndexOf("=") + 1);
        
        var date = document.getElementById("date").value;
        var days = document.getElementById("days").value;
                
        var newurl = new URL(base_url);
        newurl = newurl.toString();
        newurl = newurl.split("?")[0];
        
        var params = new URLSearchParams();
        
        params.append("key", key);
        params.append("start_date", date);
        params.append("period", days);
        
        const final_url = `${{newurl}}preview?${{params.toString()}}`;
        
        table.innerHTML = "";
        
        tablehead = table.appendChild(document.createElement("thead"));
        tablebody = table.appendChild(document.createElement("tbody"));
        
        tablehead.innerHTML = `
            <tr>
                <th>Show</th>
                <th>Season</th>
                <th>Episode</th>
                <th>Title</th>
                <th>Overview</th>
                <th>Air date</th>
            </tr>
        `;
        
        const response = await fetch(final_url);
        const data = await response.json();
        
        console.log(data);
        
        tablebody.innerHTML = data.map(item => `
            <tr>
                <td>${{item.show}}</td>
                <td>${{item.season}}</td>
                <td>${{item.number}}</td>
                <td>${{item.title}}</td>
                <td>${{item.overview}}</td>
                <td>${{item.airs_at}}</td>
            </tr>
        `).join("");
    }}
    
    editUrl();
    renderPreviewTable();
    </script>
    </html>
    """
    return page


@cache.cached(timeout=3600, query_string=["key", "start_date", "period"])
@app.route("/")
def index():
    """
    Returns ical file if key is provided, otherwise redirects to /auth
    """
    key = request.args.get("key")
    start_date = request.args.get("start_date")
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

    start_date = (
        datetime.datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
    )
    period = int(period) if period else None

    start_date_str = (
        start_date.strftime("%Y-%m-%d")
        if start_date
        else (datetime.datetime.now() - datetime.timedelta(days=30)).strftime(
            "%Y-%m-%d"
        )
    )

    try:
        col.find_one({"user_id": key})
    except Exception:
        return redirect(url_for("authorize"))
    trakt_access_token = get_token(key)

    calendar = get_calendar(
        trakt_access_token=trakt_access_token["access_token"],
        start_date=start_date,
        period=period,
    )

    with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file:
        temp_file.write(calendar)
        temp_file.flush()
        temp_file.close()

    path = os.path.join(os.path.dirname(__file__), temp_file.name)

    response = Response(open(path, "rb"), mimetype="text/calendar")
    response.headers["Cache-Control"] = "max-age=3600"
    response.headers[
        "Content-Disposition"
    ] = f"attachment; filename=trakt-calendar-{start_date_str}.ics"
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
