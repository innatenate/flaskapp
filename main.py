from flask import Flask, request, redirect, render_template
import requests
import os

app = Flask(__name__, static_folder="static", template_folder="templates")

CLIENT_ID = os.getenv("BLIZZ_CLIENT_ID")
CLIENT_SECRET = os.getenv("BLIZZ_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/authorize")
def authorize():
    auth_url = (
        f"https://oauth.battle.net/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=wow.profile"
    )
    return redirect(auth_url)

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return "No code received."

    token_url = "https://oauth.battle.net/token"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI
    }
    auth = (CLIENT_ID, CLIENT_SECRET)

    token_response = requests.post(token_url, data=data, auth=auth)
    if token_response.status_code != 200:
        return "Failed to get token."

    access_token = token_response.json()["access_token"]

    profile_url = "https://us.api.blizzard.com/profile/user/wow"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {"namespace": "profile-us", "locale": "en_US"}

    profile_response = requests.get(profile_url, headers=headers, params=params)
    if profile_response.status_code != 200:
        return "Failed to fetch profile."

    return f"Profile fetched successfully! You can close this page."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
