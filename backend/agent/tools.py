import os
import json
import uuid
import random
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pymongo import MongoClient

from services.railway_api import calculate_origin_date
from langchain_core.tools import tool
from serpapi import GoogleSearch

load_dotenv()

MONGO_URL = os.getenv("MONGO_URI", "mongodb://localhost:27017")
sync_db = MongoClient(MONGO_URL).nexustravel
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


@tool
def search_trains(source_code: str, destination_code: str, date: str) -> str:
    """
    Call this tool to search for real-time train schedules and availability.
    source_code and destination_code MUST be official Indian Railway station codes (e.g., GWL, PCOI).
    date MUST be in DD-MM-YYYY format.
    """
    print(
        f"\n👉 [SYSTEM LOG] Tool Triggered: Trains from {source_code} to {destination_code} on {date}\n"
    )

    url = "https://cttrainsapi.confirmtkt.com/api/v1/trains/search"
    params = {
        "sourceStationCode": source_code,
        "destinationStationCode": destination_code,
        "dateOfJourney": date,
        "enableNearby": "true",
        "enableTG": "true",
        "tGPlan": "CTG-A42",
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        raw_data = response.json()

        simplified_trains = []
        if "data" in raw_data and "trainList" in raw_data["data"]:

            current_date_str = datetime.now().strftime("%d-%m-%Y")
            current_time_str = datetime.now().strftime("%H:%M")

            valid_trains = []

            for train in raw_data["data"]["trainList"]:
                departure_time = train.get("departureTime", "00:00")

                if date == current_date_str and departure_time < current_time_str:
                    continue

                valid_trains.append(train)

            for train in valid_trains[:8]:

                duration_mins = int(train.get("duration", 0))
                duration_str = (
                    f"{duration_mins // 60}h {duration_mins % 60}m"
                    if duration_mins
                    else "Unknown"
                )

                availability_info = {}
                avail_cache = train.get("availabilityCache", {})
                for coach_class, details in avail_cache.items():

                    raw_status = details.get("availability")
                    raw_fare = details.get("fare")
                    raw_prediction = details.get("prediction")

                    availability_info[coach_class] = {
                        "status": (
                            raw_status
                            if raw_status is not None
                            else "Chart Prepared / N/A"
                        ),
                        "fare": raw_fare if raw_fare is not None else "N/A",
                        "prediction": (
                            raw_prediction if raw_prediction is not None else ""
                        ),
                    }
                simplified_trains.append(
                    {
                        "Train_Name": train.get("trainName", "Unknown"),
                        "Train_Number": train.get(
                            "trainNumber", train.get("trainNo", "Unknown")
                        ),
                        "Source": train.get("source", source_code),
                        "Destination": train.get("destination", destination_code),
                        "Departure": train.get("departureTime", "Unknown"),
                        "Arrival": train.get("arrivalTime", "Unknown"),
                        "Travel_Time": duration_str,
                        "Availability_and_Fares": availability_info,
                    }
                )
            return json.dumps(
                {"status": "success", "type": "trains", "data": simplified_trains}
            )

        return json.dumps(
            {
                "status": "no_trains_found",
                "message": "No trains found in the parsed data.",
            }
        )

    except Exception as e:
        return json.dumps({"status": "error", "message": f"API Error: {str(e)}"})


@tool
def search_flights(source_airport: str, destination_airport: str, date: str) -> str:
    """
    Call this tool to search for live flight schedules and prices.
    source_airport and destination_airport MUST be 3-letter IATA codes.
    date MUST be in YYYY-MM-DD format.
    """
    source = source_airport.strip().upper()
    dest = destination_airport.strip().upper()

    url = "https://google-flights2.p.rapidapi.com/api/v1/searchFlights"

    headers = {
        "x-rapidapi-key": os.getenv("RAPIDAPI_KEY"),
        "x-rapidapi-host": "google-flights2.p.rapidapi.com",
        "Content-Type": "application/json",
    }

    params = {
        "departure_id": source,
        "arrival_id": dest,
        "outbound_date": date,
        "currency": "INR",
        "travel_class": "ECONOMY",
        "adults": "1",
        "search_type": "best",
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        raw_data = response.json()

        simplified_flights = []

        if "data" in raw_data and "itineraries" in raw_data["data"]:
            itineraries = raw_data["data"]["itineraries"]
            raw_flights_list = itineraries.get("topFlights", []) + itineraries.get(
                "otherFlights", []
            )

            from datetime import datetime

            current_time = datetime.now()

            for item in raw_flights_list:

                if len(simplified_flights) >= 8:
                    break

                flight_segments = item.get("flights", [])
                if not flight_segments:
                    continue

                first_segment = flight_segments[0]

                dep_time_raw = item.get("departure_time", "00:00")
                arr_time_raw = item.get("arrival_time", "00:00")

                try:

                    time_string = dep_time_raw.strip()
                    flight_dt_str = f"{date} {time_string}"

                    try:
                        # Format check 1: 12-hour (AM/PM)
                        flight_dt = datetime.strptime(
                            flight_dt_str, "%Y-%m-%d %I:%M %p"
                        )
                    except ValueError:
                        # Format check 2: 24-hour
                        flight_dt = datetime.strptime(flight_dt_str, "%Y-%m-%d %H:%M")

                    if flight_dt < current_time:
                        continue
                except Exception as e:

                    pass

                # Clean up timings for display
                dep_time = (
                    dep_time_raw[-8:].strip()
                    if len(dep_time_raw) >= 8
                    else dep_time_raw
                )
                arr_time = (
                    arr_time_raw[-8:].strip()
                    if len(arr_time_raw) >= 8
                    else arr_time_raw
                )

                layovers = item.get("layovers")
                prediction_text = (
                    f"{len(layovers)} Stop(s)" if layovers else "Non-stop Flight"
                )

                simplified_flights.append(
                    {
                        "Train_Name": first_segment.get("airline", "Unknown Airline"),
                        "Train_Number": first_segment.get("flight_number", "Direct"),
                        "Source": source,
                        "Destination": dest,
                        "Departure": dep_time,
                        "Arrival": arr_time,
                        "Travel_Time": item.get("duration", {}).get("text", "Unknown"),
                        "Availability_and_Fares": {
                            "Economy": {
                                "status": "Available",
                                "fare": str(item.get("price", "N/A")),
                                "prediction": prediction_text,
                            }
                        },
                        "is_flight": True,
                    }
                )

            return json.dumps(
                {"status": "success", "type": "flights", "data": simplified_flights}
            )

        return json.dumps(
            {
                "status": "no_flights_found",
                "message": "Tell user no future flights found for today.",
            }
        )

    except Exception as e:
        return json.dumps({"status": "error", "message": f"API Error: {str(e)}"})


@tool
def find_accommodations(
    destination_address: str,
    stay_days: float,
    estimated_distance_km: float,
    purpose: str,
    pnr: str = "CAB9998887",
):
    """ALWAYS use this tool when the user reaches their destination and needs to book a stay."""
    response_data = {
        "recommended_type": "HOTELS",
        "reasoning": f"Since you are staying for {stay_days} days, here are the best nearby hotels with real-time availability.",
        "options": [],
    }

    try:
        check_in = datetime.now().strftime("%Y-%m-%d")
        stay_nights = max(1, int(stay_days))
        check_out = (datetime.now() + timedelta(days=stay_nights)).strftime("%Y-%m-%d")

        api_key = os.getenv("SERP_API_KEY")
        params = {
            "engine": "google_hotels",
            "q": f"Hotels in {destination_address}",
            "check_in_date": check_in,
            "check_out_date": check_out,
            "currency": "INR",
            "api_key": api_key,
        }

        search = GoogleSearch(params)
        results = search.get_dict()
        properties = results.get("properties", [])

        for prop in properties[:4]:
            # 1. Image Extraction Fix (Use original_image)
            images = prop.get("images", [])
            img_url = images[0].get("original_image") if images else ""
            if not img_url:
                img_url = (
                    images[0].get("thumbnail", "")
                    if images
                    else "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=800&q=80"
                )

            # 2. Dynamic Pricing Fix
            raw_price = prop.get("rate_per_night", {}).get("extracted_lowest", 2500)
            base_price = int(raw_price) if isinstance(raw_price, (int, float)) else 2500

            dynamic_rooms = [
                {"type": "Standard Non-AC", "price": base_price, "status": "Available"},
                {
                    "type": "Deluxe AC Room",
                    "price": int(base_price * 1.3),
                    "status": "Fast Filling",
                },
                {
                    "type": "Premium Suite",
                    "price": int(base_price * 1.8),
                    "status": "Few Left",
                },
            ]

            response_data["options"].append(
                {
                    "id": f"HTL-{prop.get('property_token', random.randint(1000,9999))}",
                    "name": prop.get("name", "Local Hotel"),
                    "description": prop.get(
                        "description", "Premium city accommodation."
                    ),
                    "price": base_price,
                    "image": img_url,
                    "rating": prop.get("overall_rating", 4.0),
                    "distance": "Near city center",
                    "amenities": prop.get(
                        "amenities",
                        ["Free Wi-Fi", "Room Service", "Power Backup", "AC"],
                    )[:5],
                    "rooms": dynamic_rooms,
                }
            )
    except Exception as e:
        print(f"Hotel API Error: {e}")

    return json.dumps(
        {"status": "success", "type": "accommodations", "data": response_data}
    )


@tool
def create_hotel_draft(
    hotel_name: str, room_type: str, price: int, pnr: str = ""
) -> str:
    """Call this tool ONLY when the user LOCKS a hotel room. MUST output [HIDDEN_HOTEL_DRAFT: {draft_id}]"""

    if not pnr or pnr == "CAB9998887":

        active_trip = sync_db.bookings.find_one(
            {
                "status": {"$regex": "Paid", "$options": "i"},
                "trip_phase": "AWAITING_ACCOMMODATION",
            }
        )

        if active_trip:
            pnr = active_trip.get("pnr", "UNKNOWN")
        else:
            pnr = "UNKNOWN"

    draft_id = f"HTL_DRAFT_{uuid.uuid4().hex[:6].upper()}"

    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
    checkout_link = f"{FRONTEND_URL}/hotel-checkout/{draft_id}"

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if token and chat_id:
        tg_message = f"🏨 ACTION REQUIRED: Secure City Stay\n\nProperty: {hotel_name}\nRoom: {room_type}\nTariff: ₹{price}/night\n\n🔗 Linked PNR: {pnr}\n\nPlease review passenger details and pay here:\n{checkout_link}"
        try:
            requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": tg_message},
            )
        except Exception:
            pass

    return json.dumps(
        {
            "status": "success",
            "type": "hotel_draft",
            "draft_id": draft_id,
            "checkout_url": checkout_link,
            "hotel_name": hotel_name,
            "room_type": room_type,
            "price": price,
            "pnr": pnr,
        }
    )


@tool
def predict_train_delay(train_name: str) -> str:
    """
    Call this tool to get the predictive delay analysis and reliability score of an Indian Railways train.
    Pass the exact train name as the argument.
    """
    print(f"\n👉 [SYSTEM LOG] Tool Triggered: Predicting Delay for {train_name}")

    name_upper = train_name.upper()

    if any(
        keyword in name_upper
        for keyword in ["VANDE BHARAT", "RAJDHANI", "SHATABDI", "DURONTO", "TEJAS"]
    ):
        status = "Low Delay Risk"
        avg_delay = random.randint(0, 15)
        reason = "Premium train with highest track clearance priority."
        reliability = "95%"

    elif any(keyword in name_upper for keyword in ["SPL", "SPECIAL", "FESTIVAL"]):
        status = "High Delay Risk"
        avg_delay = random.randint(60, 180)
        reason = "Special trains have low track priority and often wait for scheduled trains."
        reliability = "40%"

    elif any(keyword in name_upper for keyword in ["PASSENGER", "MEMU", "DEMU"]):
        status = "High Delay Risk"
        avg_delay = random.randint(45, 120)
        reason = "Passenger trains stop at all stations and frequently yield to Express trains."
        reliability = "50%"

    else:
        status = "Medium Delay Risk"
        avg_delay = random.randint(15, 45)
        reason = (
            "Standard Express/Superfast train. Subject to regular route congestion."
        )
        reliability = "75%"

    if avg_delay < 60:
        formatted_delay = f"{avg_delay} mins"
    else:
        hours = avg_delay // 60
        mins = avg_delay % 60
        if mins == 0:
            formatted_delay = f"{hours} hr"
        else:
            formatted_delay = f"{hours} hr {mins} mins"

    analysis_data = {
        "train": train_name,
        "formatted_delay": formatted_delay,
        "risk_level": status,
        "primary_reason": reason,
        "on_time_reliability": reliability,
    }

    return json.dumps(
        {"status": "success", "type": "train_delay_prediction", "data": analysis_data}
    )


@tool
def get_destination_intel(city: str, travel_date: str) -> str:
    """
    Call this tool to fetch weather and local travel intelligence for a destination.
    Pass the destination city name and the travel date (YYYY-MM-DD).
    """
    print(f"\n👉 [SYSTEM LOG] Fetching Local Intel for {city} on {travel_date}")

    api_key = os.getenv("OPENWEATHER_API_KEY")

    try:
        month_name = datetime.strptime(travel_date, "%Y-%m-%d").strftime("%B")
    except:
        month_name = "Unknown"

    weather_data = "Weather data unavailable"

    if api_key:
        try:
            url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                temp = data["main"]["temp"]
                desc = data["weather"][0]["description"].title()
                humidity = data["main"]["humidity"]
                weather_data = f"{temp}°C, {desc}, Humidity: {humidity}%"
        except Exception as e:
            print(f"❌ Weather API Error: {e}")

    analysis_data = {
        "destination": city,
        "travel_month": month_name,
        "live_weather": weather_data,
        "agent_directive": (
            "Analyze if this month is a good time to visit this city based on Indian seasons and festivals. "
            "If it's too hot/raining/crowded, WARN the user and suggest the best alternative month. "
            "If it's a good time, EXCITE the user. Give 1 local transit/packing tip and 1 food suggestion."
        ),
    }

    return json.dumps(
        {"status": "success", "type": "destination_intel", "data": analysis_data}
    )


@tool
def fetch_user_profile(user_id: str = "guest_123") -> str:
    """
    Call this tool to silently fetch the primary user's profile from the database.
    Use this to automatically fill passenger details for 'Self'.
    """
    print("\n👉 [SYSTEM LOG] Fetching Primary User Profile from DB...")

    user_data = {
        "user_id": "guest_123",
        "name": "Yogesh",
        "age": 21,
        "occupation": "Engineering Student, MNNIT",
        "phone": "+917974711962",
    }
    return json.dumps({"status": "success", "data": user_data})


@tool
def create_draft_booking(
    transit_details: str, passengers_json: str, fare_total: str
) -> str:
    """Call this tool to create a DRAFT booking and send link to Telegram."""
    draft_id = f"DRAFT_{uuid.uuid4().hex[:6].upper()}"
    checkout_link = f"{FRONTEND_URL}/checkout/{draft_id}"

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if token and chat_id:
        tg_message = f"ACTION REQUIRED: Review Booking\n\nDetails: {transit_details}\nFare: {fare_total}\n\nPlease review and pay here:\n{checkout_link}"
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        try:
            requests.post(url, json={"chat_id": chat_id, "text": tg_message})
        except Exception as e:
            print(f"Telegram Draft Error: {e}")

    return json.dumps(
        {
            "status": "success",
            "draft_id": draft_id,
            "checkout_url": checkout_link,
            "transit_details": transit_details,
            "passengers": passengers_json,
            "fare": fare_total,
        }
    )


import json
import os
import random
import requests
from datetime import datetime, timedelta


@tool
def send_booking_confirmation(
    pnr: str,
    journey_details: str,
    passengers_raw_json: str,
    train_number: str,
    baseline_probability: int,
    user_id: str,
    flight_number: str = "N/A",
    travel_class: str = "2A",
    fare: float = 1500.0,
    dep_time: str = "00:00",
    arr_time: str = "00:00",
    booking_status: str = "CNF",
    travel_date: str = "",
) -> str:
    """
    CRITICAL DIRECTIVE FOR AGENT:
    1. You MUST execute this tool to save the booking to MongoDB.
    2. 'passengers_raw_json' MUST be the EXACT raw JSON array string from the SYSTEM prompt. DO NOT summarize or format it.
    3. 'travel_date' MUST be inferred exactly from the user's context (YYYY-MM-DD).
    4. 'user_id' MUST be extracted exactly from the system prompt or conversation history context. Do not guess it.

    4. 🚨 WAITLIST & PROBABILITY DIRECTIVE (CRITICAL):
       - For TRAINS: You MUST extract the 'predictionPercentage' (e.g., 49, 74) from the search_trains API result and pass it strictly as an integer into 'baseline_probability'. DO NOT GUESS THIS VALUE.
       - For FLIGHTS or CONFIRMED TRAINS: Pass 100 as the 'baseline_probability'.

    5. 🚨 E-TICKET OUTPUT DIRECTIVE: After calling this tool, you MUST HALT all cross-selling. Do NOT ask about cabs, food, or hotels. You MUST reply to the user using EXACTLY one of the following Markdown formats depending on whether it is a Train or a Flight, and then STOP:

    🚆 IF IT IS A TRAIN JOURNEY, OUTPUT:
    🎫 **AGENTRA E-TICKET CONFIRMATION**
    ━━━━━━━━━━━━━━━━━━━━
    **PNR:** [Insert PNR]
    **Status:** PAID (Confirmed)

    🚆 **JOURNEY DETAILS:**
    [Train Name] ([Train Number]) from [Source Station] to [Destination Station]
    **Date:** [Travel Date]

    👥 **PASSENGER MANIFEST:**
    [List Passenger Name (Age, Gender) - Class | Status: [Seats]]
    ━━━━━━━━━━━━━━━━━━━━
    Have a safe and wonderful journey!

    ✈️ IF IT IS A FLIGHT JOURNEY, OUTPUT:
    ✈️ **AGENTRA E-BOARDING PASS**
    ━━━━━━━━━━━━━━━━━━━━
    **PNR / BOOKING REF:** [Insert PNR]
    **Status:** PAID (Confirmed)

    🛫 **FLIGHT DETAILS:**
    **Airlines:** [Airline Name] ([Flight Number])
    **Route:** [Source Airport/City] ➡️ [Destination Airport/City]
    **Terminal:** [Extract or randomly assign Terminal 1, 2, or 3]
    **Date:** [Travel Date]

    👥 **PASSENGER MANIFEST:**
    [List Passenger Name (Age, Gender) - Class | Status: [Seats]]
    ━━━━━━━━━━━━━━━━━━━━
    Have a safe and wonderful flight!

    6. 🚨 TRANSPORT IDENTIFIER (TRAIN vs FLIGHT):
       - If it is a TRAIN journey, extract the 5-digit train number and pass it in 'train_number'. Leave 'flight_number' as "N/A".
       - If it is a FLIGHT journey, extract the flight number (e.g., '6E-2022', 'UK-955') and pass it in 'flight_number'. Leave 'train_number' as "N/A".

    7. 🚨 STRICT TIME FORMAT DIRECTIVE (CRITICAL FOR FLIGHTS):
       - Flight timings are often displayed in AM/PM format in search results, but you MUST convert them strictly to 24-hour format (HH:MM) for the 'dep_time' and 'arr_time' parameters.
       - NEVER use 'AM' or 'PM'. NEVER append extra seconds like ':00'.
       - FLIGHT EXAMPLE 1: If an IndiGo flight departs at 10:00 PM, you MUST convert and pass exactly "22:00".
       - FLIGHT EXAMPLE 2: If a flight arrives at 12:55 AM, you MUST convert and pass exactly "00:55".
       - FLIGHT EXAMPLE 3: If a flight departs at 04:30 PM, you MUST convert and pass exactly "16:30".
       - Passing AM/PM will instantly crash the flight booking backend.
    """
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    token = os.getenv("TELEGRAM_BOT_TOKEN")

    passengers_list = []
    try:

        passengers_list = json.loads(passengers_raw_json)
    except Exception as e:
        print(f"JSON Parse failed, fallback activated. Error: {e}")
        passengers_list = [{"name": "Primary Passenger", "age": 25, "gender": "Male"}]

    primary_name = passengers_list[0].get("name", "Passenger")
    primary_gender = passengers_list[0].get("gender", "Male")
    is_solo = len(passengers_list) == 1

    import random

    allocated_details = []
    for p in passengers_list:
        name = p.get("name", "Unknown")
        age = p.get("age", "--")
        gender = p.get("gender", "U")

        if (
            "WL" in booking_status.upper()
            or "RAC" in booking_status.upper()
            or "REGRET" in booking_status.upper()
        ):
            berth_info = booking_status
        else:
            # ✈️ FLIGHT VS 🚂 TRAIN SEAT LOGIC
            if flight_number != "N/A":

                row = random.randint(2, 32)
                seat_letter = random.choice(["A", "B", "C", "D", "E", "F"])
                berth_info = f"{row}{seat_letter}"
            else:

                coach_prefix = (
                    "B"
                    if "3A" in travel_class
                    else (
                        "A"
                        if "2A" in travel_class
                        else "H" if "1A" in travel_class else "S"
                    )
                )
                berth_info = (
                    f"{coach_prefix}{random.randint(1,6)}, Seat {random.randint(1,72)}"
                )

        allocated_details.append(
            f"👤 {name} ({age}, {gender}) - Class: {travel_class} | Status: {berth_info}"
        )

    parsed_seats = "\n".join(allocated_details)

    # === PRECISE TIME PARSING ===
    try:
        base_dt = (
            datetime.strptime(travel_date, "%Y-%m-%d")
            if travel_date
            else datetime.now()
        )
    except:
        base_dt = datetime.now()

    base_date_str = base_dt.strftime("%Y-%m-%d")
    parsed_dep = f"{base_date_str}T{dep_time}:00"

    parsed_arr = f"{base_date_str}T{arr_time}:00"
    if arr_time < dep_time:
        tomorrow = base_dt + timedelta(days=1)
        parsed_arr = f"{tomorrow.strftime('%Y-%m-%d')}T{arr_time}:00"

    train_origin_date = "N/A"
    if train_number != "N/A":

        train_origin_date = calculate_origin_date(
            train_number, journey_details, travel_date
        )

    # === MONGO DB SCHEMA INSERTION ===
    booking_payload = {
        "pnr": pnr,
        "chat_id": chat_id,
        "user_id": user_id,
        "journey": journey_details,
        "train_number": train_number,
        "flight_number": flight_number,
        "departure_time": parsed_dep,
        "arrival_time": parsed_arr,
        "train_origin_date": train_origin_date,
        "passenger_name": primary_name,
        "gender": primary_gender,
        "is_solo": is_solo,
        "passengers": passengers_list,
        "seats": parsed_seats,
        "total_amount": fare,
        "expenses": [
            {
                "item_id": f"TKT_{pnr}",
                "expense_type": (
                    "TRAIN_TICKET" if train_number != "N/A" else "FLIGHT_TICKET"
                ),
                "description": journey_details,
                "cost": fare,
                "status": "BOOKED",
                "timestamp": datetime.now().isoformat(),
            }
        ],
        "status": (
            booking_status
            if "Paid" in booking_status or "PAID" in booking_status
            else f"Paid ({booking_status})"
        ),
        "timestamp": datetime.now().isoformat(),
        "baseline_probability": baseline_probability,
        "notified_wl_prediction": False,
    }

    try:
        sync_db.bookings.insert_one(booking_payload)
        print(
            f"✅ DB Update: Saved {len(passengers_list)} passengers for PNR {pnr}. Origin Date: {train_origin_date}"
        )
    except Exception as e:
        print(f"DB Save Error: {e}")

    # === TELEGRAM NOTIFICATION PUSH ===
    if token and chat_id:
        if flight_number != "N/A":
            import random

            terminal_mock = f"Terminal {random.randint(1,3)}"

            msg = (
                f"✈️ <b>AGENTRA E-BOARDING PASS</b> ✈️\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🎫 <b>PNR / REF:</b> <code>{pnr}</code>\n"
                f"✅ <b>Status:</b> PAID ({booking_status})\n\n"
                f"🛫 <b>FLIGHT DETAILS:</b>\n"
                f"{journey_details}\n"
                f"🏢 <b>Terminal:</b> {terminal_mock}\n"
                f"📅 <b>Date:</b> {base_date_str}\n\n"
                f"👥 <b>PASSENGER MANIFEST:</b>\n{parsed_seats}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"<i>Have a safe and wonderful flight! ☁️</i>"
            )
        else:
            msg = (
                f"🎫 <b>AGENTRA E-TICKET CONFIRMATION</b> 🎫\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🎫 <b>PNR:</b> <code>{pnr}</code>\n"
                f"✅ <b>Status:</b> PAID ({booking_status})\n\n"
                f"🚆 <b>JOURNEY DETAILS:</b>\n"
                f"{journey_details}\n"
                f"📅 <b>Date:</b> {base_date_str}\n\n"
                f"👥 <b>PASSENGER MANIFEST:</b>\n{parsed_seats}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"<i>Have a safe and wonderful journey! 🚂</i>"
            )

        try:
            requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"},
            )
        except Exception as e:
            print(f"Telegram Push Error: {e}")

    # === DYNAMIC TOOL RESPONSE FOR LLM ===
    if flight_number != "N/A":
        tool_response_msg = (
            f"Booking successful for PNR {pnr}. Reply to the user with a nice markdown formatted E-Boarding Pass summary "
            f"(Include PNR/Ref, Airline & Flight {flight_number}, Route, Date, and Passenger Seats {parsed_seats}). "
            f"After providing this summary, YOU MUST STOP. DO NOT say 'Welcome to the destination' or ask about cabs/hotels."
        )
    else:
        tool_response_msg = (
            f"Booking successful for PNR {pnr}. Reply to the user with a nice markdown formatted E-Ticket summary "
            f"(Include PNR, Train, Route, Date, and Passenger Seats {parsed_seats}). "
            f"After providing this summary, YOU MUST STOP. DO NOT say 'Welcome to the destination' or ask about cabs/hotels."
        )

    return json.dumps({"status": "success", "message": tool_response_msg})


# Register all tools to be passed to the agent
travel_tools = [
    search_trains,
    search_flights,
    predict_train_delay,
    get_destination_intel,
    fetch_user_profile,
    create_draft_booking,
    send_booking_confirmation,
    find_accommodations,
    create_hotel_draft,
]
