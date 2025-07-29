import threading
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import os

# Load environment variables from .env file at the very start
load_dotenv()

# Initialize Flask API app
api_app = Flask(__name__)

# Import and register routes
# This import needs to happen AFTER api_app is initialized
# to avoid circular import issues if routes.py references api_app
from munich_path.api import routes
routes.init_app_routes(api_app) # A function to register routes will be better


def start_api_server():
    """
    Starts the Flask API server in a separate thread.
    This is useful for running the API alongside a Streamlit app locally.
    In a production environment, the Flask API would typically be run
    independently (e.g., using Gunicorn, uWSGI, or deployed as a separate service).
    """
    try:
        # debug=False and use_reloader=False are crucial when running Flask
        # in a separate thread, especially from another process like Streamlit.
        # Otherwise, it can cause issues like the server starting multiple times.
        print("Starting Flask API server on http://0.0.0.0:5000...")
        api_app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    except Exception as e:
        print(f"Failed to start Flask API server: {e}")

# You can optionally add a main guard for direct execution of the API for testing
if __name__ == '__main__':
    # This block would typically be for standalone API testing/running
    # not usually called when run via Streamlit's threading.
    print("Running API directly (for testing purposes)...")
    start_api_server()
