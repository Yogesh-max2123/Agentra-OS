import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os

MONGO_URL = os.getenv("MONGO_URI", "mongodb://localhost:27017")

client = AsyncIOMotorClient(MONGO_URL)
db = client.nexustravel


async def init_db():
    try:

        await client.admin.command("ping")

        user = await db.users.find_one({"user_id": "guest_123"})

        if not user:
            await db.users.insert_one(
                {
                    "user_id": "guest_123",
                    "name": "Yogesh",
                    "age": 21,
                    "occupation": "Engineering Student, MNNIT",
                    "frequent_routes": ["GWL", "PRYJ"],
                    "phone": "+917974711962",
                }
            )
            print("✅ MongoDB Connected: Default User Profile Created!")
        else:
            print(
                "✅ MongoDB Connected: User Profile already exists in 'nexustravel' DB!"
            )

    except Exception as e:
        print(f"❌ MongoDB Connection Error: {e}")
