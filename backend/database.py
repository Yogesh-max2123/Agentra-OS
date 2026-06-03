# backend/database.py
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = "mongodb://localhost:27017"
client = AsyncIOMotorClient(MONGO_URL)
db = client.nexustravel

async def init_db():
    try:
        # Check connection by pinging the database
        await client.admin.command('ping')
        
        # Check if user exists
        user = await db.users.find_one({"user_id": "guest_123"})
        
        if not user:
            await db.users.insert_one({
                "user_id": "guest_123",
                "name": "Yogesh", # Ya tumhara jo bhi naam ho
                "age": 21,
                "occupation": "Engineering Student, MNNIT",
                "frequent_routes": ["GWL", "PRYJ"],
                "phone": "+919999999999" # Notification ke liye
            })
            print("✅ MongoDB Connected: Default User Profile Created!")
        else:
            print("✅ MongoDB Connected: User Profile already exists in 'nexustravel' DB!")
            
    except Exception as e:
        print(f"❌ MongoDB Connection Error: {e}")