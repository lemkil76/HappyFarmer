"""
HappyFarmer - Social Media Integration
integrations/social_media.py  (renamed from TwitterPOC.py)
Revised by Claude - 2026-03-20

Uses tweepy + X/Twitter API v2.
Set env vars - see docs/SETUP.md step 4.

Install: pip install tweepy
"""

import os
import tweepy

# ── Credentials from environment variables ────────────────────────────────────
BEARER_TOKEN  = os.environ.get("HAPPYFARMER_BEARER_TOKEN")
API_KEY       = os.environ.get("HAPPYFARMER_API_KEY")
API_SECRET    = os.environ.get("HAPPYFARMER_API_SECRET")
ACCESS_TOKEN  = os.environ.get("HAPPYFARMER_ACCESS_TOKEN")
ACCESS_SECRET = os.environ.get("HAPPYFARMER_ACCESS_SECRET")

# ── Client (API v2) ────────────────────────────────────────────────────────────
client = tweepy.Client(
    bearer_token=BEARER_TOKEN,
    consumer_key=API_KEY,
    consumer_secret=API_SECRET,
    access_token=ACCESS_TOKEN,
    access_token_secret=ACCESS_SECRET,
    wait_on_rate_limit=True,
)

comment_lib = [
    "Glad bonde onskar dig en harlig dag!",
    "Har kan du folja progressen pa bygget",
    "Glad bonde anvander Python och Raspberry Pi",
    "Sensorer: lufttemp, vattentemp, luftfuktighet, fotoresistor",
]


def post_sensor_update(air_temp, water_temp, humidity, light_level):
    """Post daily sensor data. Called every 4th day from core/main.py."""
    message = (
        f"HappyFarmer daglig rapport\n"
        f"Lufttemp: {air_temp:.1f}C | Vattentemp: {water_temp:.1f}C\n"
        f"Luftfuktighet: {humidity:.0f}% | Ljus: {light_level}\n"
        f"#verticalfarming #hydroponics #raspberrypi"
    )
    try:
        response = client.create_tweet(text=message)
        print(f"Tweet posted: id={response.data['id']}")
        return response.data["id"]
    except tweepy.TweepyException as e:
        print(f"[ERROR] Failed to post tweet: {e}")
        return None


def post_timelapse_update(image_path: str):
    """Post timelapse image every 30 days. Media upload uses v1.1 endpoint."""
    try:
        auth   = tweepy.OAuth1UserHandler(API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET)
        api_v1 = tweepy.API(auth)
        media  = api_v1.media_upload(filename=image_path)
        response = client.create_tweet(
            text="HappyFarmer timelapse - en manads tillvaxt! #verticalfarming",
            media_ids=[media.media_id],
        )
        print(f"Timelapse tweet posted: id={response.data['id']}")
        return response.data["id"]
    except tweepy.TweepyException as e:
        print(f"[ERROR] Failed to post timelapse: {e}")
        return None


def verify_credentials():
    """Test credentials at startup."""
    try:
        me = client.get_me()
        print(f"Connected as: @{me.data.username}")
        return True
    except tweepy.TweepyException as e:
        print(f"[ERROR] Credential check failed: {e}")
        return False


if __name__ == "__main__":
    if verify_credentials():
        post_sensor_update(air_temp=22.5, water_temp=20.1, humidity=65, light_level="dag")
