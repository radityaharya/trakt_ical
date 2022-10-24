from flask import Flask, Response, request
from flask_caching import Cache
from ical import main as trakt_ical

config = {
    "DEBUG": True,
    "CACHE_TYPE": "SimpleCache",
    "CACHE_DEFAULT_TIMEOUT": 3600
}
app = Flask(__name__)
app.config.from_mapping(config)
cache = Cache(app)

@app.route("/trakt.ics")
@cache.cached(timeout=3600)
def trakt_ical_endpoint():
    return Response(trakt_ical(), mimetype="text/calendar")

def serve(host:str, port:int, debug:bool):
    app.run(host=host, port=port, debug=debug)