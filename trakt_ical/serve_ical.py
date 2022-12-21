from flask import Flask, Response, request
from flask_caching import Cache
from ical import main as trakt_ical
import os

config = {
    "DEBUG": True,
    "CACHE_TYPE": "SimpleCache",
    "CACHE_DEFAULT_TIMEOUT": 3600
}
app = Flask(__name__)
app.config.from_mapping(config)
cache = Cache(app)

@app.route("/")
@cache.cached(timeout=3600, query_string=True)
def trakt_ical_endpoint():
    key = request.args.get("key")
    if key != os.environ.get("TRAKT_ICAL_KEY"):
        return Response("Invalid key", status=401)
    return Response(trakt_ical(), mimetype="text/calendar")

def serve(host:str = "0.0.0.0", port:int = "8000", debug:bool = False):
    app.run(host=host, port=port, debug=debug)