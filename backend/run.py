"""
Entrypoint for starting MediTrack AI Assistant backend server.
Supports both Flask development server and Waitress production WSGI server.
"""
import os
import sys
import argparse
from app import create_app

app = create_app()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start MediTrack AI Backend Server")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", 5000)), help="Port to bind to")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host interface to bind to")
    parser.add_argument("--prod", action="store_true", help="Run with Waitress production WSGI server")
    args = parser.parse_args()

    if args.prod:
        from waitress import serve
        print(f">> Starting MediTrack AI with Waitress WSGI on http://{args.host}:{args.port}")
        serve(app, host=args.host, port=args.port, threads=8)
    else:
        print(f">> Starting MediTrack AI development server on http://{args.host}:{args.port}")
        app.run(host=args.host, port=args.port, debug=app.config.get("FLASK_DEBUG", True))
