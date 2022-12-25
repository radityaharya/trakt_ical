import argparse
from serve_ical import serve


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", help="Serve the ical file", action='store_true')
    parser.add_argument("--host", help="Host to serve the ical file", default="0.0.0.0")
    parser.add_argument("--port", help="Port to serve the ical file", default=8000)
    parser.add_argument("--debug", help="Debug mode", default= False)
    
    args = parser.parse_args()
    
    if args.serve:
        print("Serving the ical file")
        serve(args.host, args.port, args.debug)