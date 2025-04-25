import redis.asyncio as redis
import asyncio

async def main():
    r = redis.from_url("redis://localhost:6379/0", encoding="utf-8", decode_responses=True)
    try:
        pong = await r.ping()
        print(f"Redis ping response: {pong}")
    except Exception as e:
        print(f"Redis ping failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
