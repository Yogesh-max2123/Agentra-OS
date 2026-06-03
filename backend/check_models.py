import google.generativeai as genai
import os
from dotenv import load_dotenv

# .env load karna aur key set karna
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

print("Fetching available models from Google Servers...\n")

# Server se pooch rahe hain kaunse models generateContent support karte hain
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"✅ Available: {m.name}")
except Exception as e:
    print(f"Error fetching models: {e}")