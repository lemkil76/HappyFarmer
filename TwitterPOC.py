"""
HappyFarmer - Social Media Integration
Revised by Claude - 2026-03-20

Replaces the old python-twitter (v1 API) with tweepy and X/Twitter API v2.
Requires a free-tier X Developer account with OAuth 2.0 Bearer Token
and OAuth 1.0a keys for posting (write access).

Install dependency:
    pip install tweepy

    Environment variables to set (never hardcode credentials):
        HAPPYFARMER_BEARER_TOKEN
            HAPPYFARMER_API_KEY
                HAPPYFARMER_API_SECRET
                    HAPPYFARMER_ACCESS_TOKEN
                        HAPPYFARMER_ACCESS_SECRET
                        """

import os
import tweepy

# -- Credentials ---------------------------------------------------------------
# Load from environment variables - never commit real keys to source control!
BEARER_TOKEN  = os.environ.get("HAPPYFARMER_BEARER_TOKEN")
API_KEY       = os.environ.get("HAPPYFARMER_API_KEY")
API_SECRET    = os.environ.get("HAPPYFARMER_API_SECRET")
ACCESS_TOKEN  = os.environ.get("HAPPYFARMER_ACCESS_TOKEN")
ACCESS_SECRET = os.environ.get("HAPPYFARMER_ACCESS_SECRET")

# -- Client (API v2) -----------------------------------------------------------
client = tweepy.Client(
      bearer_token=BEARER_TOKEN,
      consumer_key=API_KEY,
      consumer_secret=API_SECRET,
      access_token=ACCESS_TOKEN,
      access_token_secret=ACCESS_SECRET,
      wait_on_rate_limit=True
)

# -- Comment library (Swedish) -------------------------------------------------
comment_lib = [
      "Glad bonde onskar dig en harlig dag!",
      "Har kan du folja progressen pa bygget",
      "Glad bonde anvander Python och Raspberry Pi",
      "Sensorer: lufttemp, vattentemp, luftfuktighet, fotoresistor",
]

# -- Post a status update ------------------------------------------------------
def post_sensor_update(air_temp, water_temp, humidity, light_level):
      """Post daily sensor data. Called every 4th day from main loop."""
      message = (
          f"HappyFarmer daglig rapport\n"
          f"Lufttemp: {air_temp:.1f}C | Vattentemp: {water_temp:.1f}C\n"
          f"Luftfuktighet: {humidity:.0f}% | Ljus: {light_level}\n"
          f"#verticalfarming #hydroponics #raspberrypi"
      )
      try:
                response = client.create_tweet(text=message)
                print(f"Tweet posted: id={response.data['id']}")
                return response.data['id']
except tweepy.TweepyException as e:
        print(f"[ERROR] Failed to post tweet: {e}")
        return None

# -- Post timelapse (every 30 days) --------------------------------------------
def post_timelapse_update(image_path: str):
      """
          Post a timelapse image to X/Twitter.
              Media upload uses v1.1 endpoint via tweepy.API.
                  """
      try:
                auth = tweepy.OAuth1UserHandler(API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET)
                api_v1 = tweepy.API(auth)
                media = api_v1.media_upload(filename=image_path)
                response = client.create_tweet(
                    text="HappyFarmer timelapse - en manads tillvaxt! #verticalfarming",
                    media_ids=[media.media_id]
                )
                print(f"Timelapse tweet posted: id={response.data['id']}")
                return response.data['id']
except tweepy.TweepyException as e:
        print(f"[ERROR] Failed to post timelapse: {e}")
        return None

# -- Verify connection ---------------------------------------------------------
def verify_credentials():
      """Test that credentials are valid. Call at startup."""
      try:
                me = client.get_me()
                print(f"Connected as: @{me.data.username}")
                return True
except tweepy.TweepyException as e:
        print(f"[ERROR] Credential check failed: {e}")
        return False


if __name__ == "__main__":
      if verify_credentials():
                # Example: post a test update with dummy sensor values
                post_sensor_update(
                              air_temp=22.5,
                              water_temp=20.1,
                              humidity=65,
                              light_level="dag"
                )
