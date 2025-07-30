from flask import Flask, request, redirect, render_template
import requests
import os
import logging
import secrets
from urllib.parse import quote
import json

# Enable debug-level logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__, static_folder="static", template_folder="templates")

# Environment variables
CLIENT_ID = os.getenv("BLIZZARD_CLIENT_ID")
CLIENT_SECRET = os.getenv("BLIZZARD_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
FASTAPI_WEBHOOK_URL = os.getenv("FASTAPI_WEBHOOK_URL")  # e.g., https://your-fastapi.up.railway.app/onboard

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/authorize")
def authorize():
    state = secrets.token_urlsafe(16)
    discord_id = request.args.get("discord_id")  # from the bot’s link

    if not discord_id:
        return "Missing Discord ID", 400

    # Store the Discord ID in session or temp file/db if needed

    auth_url = (
        "https://oauth.battle.net/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={quote(REDIRECT_URI)}"
        f"&response_type=code"
        f"&scope=wow.profile"
        f"&state={discord_id}"  # embed discord ID into state
    )

    return redirect(auth_url)

@app.route("/callback")
def callback():
    code = request.args.get("code")
    discord_id = request.args.get("state")  # retrieved from the original request

    if not code or not discord_id:
        return "Missing code or Discord ID", 400

    # Exchange code for access token
    token_url = "https://oauth.battle.net/token"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI
    }
    auth = (CLIENT_ID, CLIENT_SECRET)

    token_response = requests.post(token_url, data=data, auth=auth)

    if token_response.status_code != 200:
        print("TOKEN ERROR:", token_response.status_code)
        print("RESPONSE:", token_response.text)
        return "Failed to get token."

    access_token = token_response.json().get("access_token")

    # Fetch user profile
    profile_url = "https://us.api.blizzard.com/profile/user/wow"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {"namespace": "profile-us", "locale": "en_US"}

    profile_response = requests.get(profile_url, headers=headers, params=params)

    if profile_response.status_code != 200:
        print("PROFILE ERROR:", profile_response.status_code)
        print("RESPONSE:", profile_response.text)
        return "Failed to fetch profile."

    profile_data = profile_response.json()

    characters = profile_data.get("wow_accounts", [])[0].get("characters", [])

    # Send character list to FastAPI
    try:
        payload = {
            "discord_id": int(discord_id),
            "characters": characters  # Pass full character objects directly
        }


        requests.post(FASTAPI_WEBHOOK_URL, json=payload)
    except Exception as e:
        logging.error(f"Error sending data to FastAPI: {e}")
        return "Failed to send data to bot."

    return render_template("callback.html", characters=payload["characters"])
