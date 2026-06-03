import re
import os
import random
import requests
from pymongo import MongoClient
from services.railway_api import get_live_train_status

# Ensure you have your Telegram Bot Token in your .env file
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
sync_db = MongoClient("mongodb://localhost:27017").nexustravel

def trigger_pre_departure_workflow(chat_id: str, pnr: str):
    """
    Executes the Pre-Departure Workflow for the specified booking (Train or Flight).
    """
    # 1. Fetch exact booking from DB using the passed PNR
    latest_booking = sync_db.bookings.find_one({"pnr": pnr})
    if not latest_booking:
        return {"status": "error", "message": f"No booking found for PNR {pnr}."}
        
    is_flight = latest_booking.get("flight_number", "N/A") != "N/A"
    journey_details = latest_booking.get("journey", "")
    
    # 2. Extract Real Seat Info from DB (Allocated during booking confirmation)
    seats_info = latest_booking.get("seats", "Unassigned")
    # Clean up to show just the seat number
    seat_only = seats_info.split("Status: ")[-1] if "Status: " in seats_info else seats_info

    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    send_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    if is_flight:
        # ==========================================
        # ✈️ FLIGHT PRE-DEPARTURE WORKFLOW
        # ==========================================
        flight_number = latest_booking.get("flight_number", "Unknown")
        
        # Flight Telegram Message (Transit)
        telegram_msg = (
            f"✈️ <b>FLIGHT DEPARTURE ALERT</b> ✈️\n\n"
            f"🎫 <b>PNR / REF:</b> <code>{pnr}</code>\n"
            f"🛫 <b>Flight:</b> {flight_number}\n\n"
            f"✅ <b>Status:</b> WEB CHECK-IN OPEN\n"
            f"💺 <b>Allocated Seat:</b> {seat_only}\n\n"
            f"🚕 <b>Airport Transit:</b>\n"
            f"Your flight departs in a few hours. Shall I book an Airport Cab (Rapido/Ola) from your current location to the Airport? (Payment directly to driver)"
        )
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "🚕 Book Airport Cab", "callback_data": f"book_cab_{pnr}"}],
                [{"text": "No, I'll manage myself", "callback_data": "ignore_cab"}]
            ]
        }
        
        # Flight Food/Lounge Message
        food_msg = (
            f"🍱 <b>In-Flight Meals & Lounge</b>\n\n"
            f"Would you like to pre-book a meal for the flight? I can add a fresh sandwich to your booking, or even arrange airport lounge access for a relaxed wait!"
        )
        
        food_keyboard = {
            "inline_keyboard": [
                [{"text": "🍔 Pre-book Meal", "callback_data": f"flight_food_{pnr}"}],
                [{"text": "🛋️ Lounge Access", "callback_data": f"lounge_access_{pnr}"}],
                [{"text": "No, I'm good", "callback_data": "food_no"}]
            ]
        }

    else:
        # ==========================================
        # 🚂 TRAIN PRE-DEPARTURE WORKFLOW
        # ==========================================
        train_number = latest_booking.get("train_number", "UNKNOWN")
        if train_number == "UNKNOWN":
            train_no_match = re.search(r'\((\d{5})\)', journey_details)
            train_number = train_no_match.group(1) if train_no_match else "12004"
        
        # 3. Fetch Live Status via RapidAPI (ONLY FOR TRAINS)
        current_station = "Fetching live location..."
        delay_status = "🟢 Checking status..."
        
        # 🚨 NEW MASTER KEY FIX: DB se exact Origin Date uthao
        import datetime
        origin_date = latest_booking.get("train_origin_date", datetime.datetime.now().strftime("%Y%m%d"))
        
        try:
            live_data = get_live_train_status(train_number, origin_date)
            if live_data and "body" in live_data:
                data_body = live_data["body"]
                
                # 1. Asli Current Station ka message (e.g., "Train has crossed...")
                current_station = data_body.get("train_status_message", "En route to your station")
                
                # 2. Delay aur Boarding ETA calculate karna
                stations_list = data_body.get("stations", [])
                current_station_code = data_body.get("current_station", "")
                delay_mins = 0
                boarding_eta = ""
                
                # Extract Boarding Station from "CHATTISGARH EXP (18237) from GWL to AGC"
                boarding_code = ""
                if " from " in journey_details and " to " in journey_details:
                    boarding_code = journey_details.split(" from ")[1].split(" to ")[0].strip()
                
                for stn in stations_list:
                    # Calculate exact delay using current live station
                    if stn.get("stationCode") == current_station_code:
                        sch_time = stn.get("departureTime", stn.get("arrivalTime", ""))
                        act_time = stn.get("actual_departure_time", stn.get("actual_arrival_time", ""))
                        if sch_time and act_time and ":" in sch_time and ":" in act_time:
                            try:
                                sh, sm = map(int, sch_time.split(":"))
                                ah, am = map(int, act_time.split(":"))
                                diff = (ah * 60 + am) - (sh * 60 + sm)
                                if diff < -720: diff += 1440
                                delay_mins = diff
                            except:
                                pass
                                
                    # Find ETA for the User's Boarding Station
                    if boarding_code and stn.get("stationCode", "").upper() == boarding_code.upper():
                        boarding_eta = stn.get("actual_departure_time", stn.get("departureTime", ""))

                # Formatting the final Output
                if delay_mins > 0:
                    delay_status = f"🔴 Delayed by {delay_mins} mins"
                elif delay_mins < 0:
                    delay_status = f"🟢 Early by {abs(delay_mins)} mins"
                else:
                    delay_status = "🟢 Running On Time"
                    
                # Append ETA to the message if we found their station
                if boarding_eta:
                    delay_status += f" (ETA at {boarding_code}: {boarding_eta})"
                    
        except Exception as e:
            print(f"Pre-Departure Live status error: {e}")
        
        # Train Telegram Message (Transit)
        telegram_msg = (
            f"🚨 <b>CHART PREPARED - ACTION REQUIRED</b> 🚨\n\n"
            f"🎫 <b>PNR:</b> <code>{pnr}</code>\n"
            f"🚆 <b>Train:</b> {train_number}\n\n"
            f"✅ <b>Ticket Status:</b> CONFIRMED\n"
            f"💺 <b>Allocated Seat:</b> {seat_only}\n\n"
            f"📡 <b>Live Transit Status:</b>\n"
            f"📍 Currently at: {current_station}\n"
            f"⏳ Timing: {delay_status}\n\n"
            f"Since your departure is in 1.5 hours, shall I book a local Rapido/Ola from your current location to the station?"
        )
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "🚕 Book Cab to Station", "callback_data": f"book_cab_{pnr}"}],
                [{"text": "No, I'll manage myself", "callback_data": "ignore_cab"}]
            ]
        }
        
        # Train Food Message
        food_msg = (
            f"🍱 <b>In-Transit Dining Service</b>\n\n"
            f"Have you packed your food for the journey? If you're in a rush, I can order a fresh Masala Dosa to your seat, or you can request anything else from the E-Catering menu."
        )
        
        food_keyboard = {
            "inline_keyboard": [
                [{"text": "🍛 Order Masala Dosa", "callback_data": f"food_usual_{pnr}"}],
                [{"text": "🍕 Order Something Else", "callback_data": f"food_custom_{pnr}"}],
                [{"text": "No, I'm good", "callback_data": "food_no"}]
            ]
        }

    # ==========================================
    # 7. SEND MESSAGES TO TELEGRAM
    # ==========================================
    
    # Send Transit Message
    payload = {
        "chat_id": chat_id,
        "text": telegram_msg,
        "parse_mode": "HTML",
        "reply_markup": keyboard
    }
    requests.post(send_url, json=payload)
    
    # Send Food Orchestration Message
    food_payload = {
        "chat_id": chat_id,
        "text": food_msg,
        "parse_mode": "HTML",
        "reply_markup": food_keyboard
    }
    requests.post(send_url, json=food_payload)
    
    return {"status": "success", "message": f"Pre-departure workflow executed for PNR {pnr}."}


# ---------------------------------------------------------
# PHASE 2: IN-TRANSIT & POST-BOARDING ORCHESTRATION
# ---------------------------------------------------------

def trigger_post_boarding_checkin(chat_id: str, pnr: str):
    """Triggered 20 minutes after actual departure"""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    msg = (
        f"🎒 <b>Boarding Check-In! (PNR: {pnr})</b>\n\n"
        f"Hey! Did you board the train successfully? I hope you've found your seat and settled your luggage securely. "
        f"Have you arranged your beddings?\n\n"
        f"Relax and enjoy your journey. I'll be awake and tracking the train for you so you can sleep peacefully! 🌙"
    )
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "✅ Yes, all settled!", "callback_data": "ack_settled"}],
            [{"text": "I need help (Fetch TT Info)", "callback_data": "help_tt"}]
        ]
    }
    
    requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", 
                  json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML", "reply_markup": keyboard})
    return {"status": "Post-boarding check-in sent."}


def trigger_wake_up_call(chat_id: str, pnr: str, destination: str = "Prayagraj Junction"):
    """Triggered dynamically 30 mins before the latest ETA"""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    msg = (
        f"⏰ <b>WAKE UP CALL!</b> ⏰\n\n"
        f"Good morning! Your train is just 30 minutes away from <b>{destination}</b>.\n\n"
        f"🧳 Please wake up, freshen up, and double-check your berths to ensure you've packed all your belongings, chargers, and bags.\n\n"
        f"Shall I book a local transit (Rapido/Cab) to take you from the station to your final destination (like campus/home)?"
    )
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "🚕 Yes, Book a Cab", "callback_data": f"book_cab_{pnr}"}],
            [{"text": "No, I'm good", "callback_data": "ignore_cab"}]
        ]
    }
    
    requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", 
                  json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML", "reply_markup": keyboard})
    return {"status": "Wake-up call sent."}



def trigger_pre_arrival_transit(chat_id: str, pnr: str, passenger_name: str):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    transit_msg = (
        f"🚉 <b>Destination Approaching!</b>\n\n"
        f"Hi {passenger_name}, you will reach your destination in exactly 10 minutes.\n"
        f"Do you need a ride to your final specific address? Let me know based on your luggage:"
    )
    keyboard = {
        "inline_keyboard": [
            [{"text": "🧳 Heavy Luggage (Book Ola Cab)", "callback_data": "transit_cab"}],
            [{"text": "🎒 Light Luggage (Book Rapido Bike)", "callback_data": "transit_bike"}],
            [{"text": "🚌 I will use Local Transit", "callback_data": "transit_local"}]
        ]
    }
    requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", 
                  json={"chat_id": chat_id, "text": transit_msg, "parse_mode": "HTML", "reply_markup": keyboard})


# ---------------------------------------------------------
# PHASE 3: PROJECT SHAKTI & GLOBAL SOS INITIALIZATION
# ---------------------------------------------------------

def trigger_project_shakti_onboarding(chat_id: str, pnr: str, passenger_name: str):
    """Triggered after booking confirmation for solo female travelers."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    # 1. Attach the Persistent Global SOS Keyboard (Stays at the bottom always)
    persistent_keyboard = {
        "keyboard": [
            [{"text": "🚨 EMERGENCY SOS"}]
        ],
        "resize_keyboard": True,
        "persistent": True
    }
    
    # Send a silent setup message to lock the SOS button on their screen
    requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", 
                  json={"chat_id": chat_id, "text": "🛡️ Emergency protocols loaded.", "reply_markup": persistent_keyboard})
    
    # 2. Send the Project Shakti Comfort Message
    shakti_msg = (
        f"🌸 <b>Project Shakti - Solo Traveler Shield</b>\n\n"
        f"Hi {passenger_name}, I noticed you are traveling solo today. "
        f"Please know that you are not alone; Agentra is riding with you digitally.\n\n"
        f"I have pre-linked your PNR ({pnr}) with the RPF Women's Squad for this route. "
        f"Would you like to activate the Shakti Shield for this journey?"
    )
    
    inline_keyboard = {
        "inline_keyboard": [
            [{"text": "🛡️ Activate Shakti Shield", "callback_data": f"activate_shakti_{pnr}"}]
        ]
    }
    
    requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", 
                  json={"chat_id": chat_id, "text": shakti_msg, "parse_mode": "HTML", "reply_markup": inline_keyboard})
    return {"status": "Project Shakti initialized."}