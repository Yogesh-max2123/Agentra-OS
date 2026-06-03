import os
from serpapi import GoogleSearch
from datetime import datetime, timedelta
from dotenv import load_dotenv
import json

# Load env variables to get the API key
load_dotenv()

def test_google_hotels_api():
    api_key = os.getenv("SERP_API_KEY")
    
    if not api_key:
        print("❌ ERROR: SERP_API_KEY not found in .env file!")
        return

    # Same logic as your agent
    check_in = datetime.now().strftime("%Y-%m-%d")
    check_out = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
    
    params = {
        "engine": "google_hotels",
        "q": "Hotels in Connaught Place, New Delhi",
        "check_in_date": check_in,
        "check_out_date": check_out,
        "currency": "INR",
        "api_key": api_key
    }

    print("⏳ Hitting SerpAPI Google Hotels...")
    try:
        search = GoogleSearch(params)
        results = search.get_dict()
        
        # Checking for errors in response
        if "error" in results:
            print(f"\n❌ API RETURNED ERROR: {results['error']}")
            return

        properties = results.get("properties", [])
        print(f"\n✅ SUCCESS! Found {len(properties)} hotels.")
        
        if len(properties) > 0:
            print("\n🏨 TOP 2 HOTELS FOUND:")
            for prop in properties[:2]:
                print(json.dumps(prop, indent=2))
        else:
            print("\n⚠️ API returned an empty list. No hotels found for this query/date.")
            print("Full Raw Response:")
            print(json.dumps(results, indent=2))

    except Exception as e:
        print(f"\n❌ CRITICAL CRASH: {str(e)}")

if __name__ == "__main__":
    test_google_hotels_api()