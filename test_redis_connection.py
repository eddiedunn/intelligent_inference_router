import os
from dotenv import load_dotenv
import redis

load_dotenv()  # This loads environment variables from .env

url = os.environ.get("REDIS_URL")
print("Connecting to:", url)
r = redis.from_url(url)
try:
    print("PING:", r.ping())
except Exception as e:
    print("ERROR:", e)
