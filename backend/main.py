import asyncio
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router
from database import init_db
from pymongo import MongoClient
import os
from fastapi import FastAPI, Request, BackgroundTasks, Form, Response
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import requests
import random
from pydantic import BaseModel
from typing import List, Dict


from models.schemas import BookingSchema, ExpenseItem
from services.invoice_generator import generate_trip_invoice, send_invoice_via_telegram

from services.railway_api import get_live_train_status

from predictive_engine import run_smart_wl_prediction


from services.orchestrator import (
    trigger_pre_departure_workflow,
    trigger_post_boarding_checkin,
    trigger_wake_up_call,
    trigger_project_shakti_onboarding,
    trigger_pre_arrival_transit,
)


# ---------------------------------------------------------
# 🤖 THE MASTER AUTOPILOT ENGINE
# ---------------------------------------------------------
def master_timetable_checker():
    print(
        f"[{datetime.now().strftime('%H:%M:%S')}] 🤖 Autopilot: Checking upcoming journeys..."
    )

    try:

        bookings = db.bookings.find({"status": {"$regex": "Paid", "$options": "i"}})
        current_time = datetime.now()

        for booking in bookings:
            if "departure_time" not in booking or "chat_id" not in booking:
                continue

            pnr = booking.get("pnr")
            chat_id = booking.get("chat_id")
            passenger_name = booking.get("passenger_name", "Passenger")
            gender = booking.get("gender", "Male").upper()
            is_solo = booking.get("is_solo", False)

            # ✈️ NEW: FLIGHT DETECTOR (Direct from DB)
            flight_no = booking.get("flight_number", "N/A")
            is_flight = True if flight_no != "N/A" else False

            raw_dep = booking["departure_time"].replace("Z", "")
            if "+" in raw_dep:
                raw_dep = raw_dep.split("+")[0]

            dep_time = datetime.fromisoformat(raw_dep)
            time_diff = dep_time - current_time
            diff_minutes = time_diff.total_seconds() / 60

            transport_icon = "✈️" if is_flight else "🚂"
            print(
                f"   [Debug] {transport_icon} PNR {pnr} | T-Minus: {diff_minutes:.1f} mins | Status: {booking.get('status')}"
            )

            # -----------------------------------------------------------
            # SMART WL PREDICTION (Triggered ~24 Hours / 1440 mins before)
            # -----------------------------------------------------------

            if 1400 <= diff_minutes <= 1440 and not booking.get(
                "notified_wl_prediction"
            ):
                status_text = booking.get("status", "").upper()

                if "WL" in status_text or "RAC" in status_text:
                    print(f"🤖 Triggering Smart WL Engine for PNR: {pnr}")

                    prediction_data = run_smart_wl_prediction(booking)
                    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
                    chat_id = booking.get("chat_id")

                    if prediction_data.get("prediction_status") == "WILL_DROP":
                        alts_text = "\n".join(
                            prediction_data.get("smart_alternatives", [])
                        )

                        msg = (
                            f"⚠️ <b>AGENTRA SMART WAITLIST ALERT</b> ⚠️\n\n"
                            f"PNR: <b>{pnr}</b>\n"
                            f"Based on real-time AI analysis, your ticket has an adjusted <b>{prediction_data['adjusted_probability']}% chance</b> of confirming.\n\n"
                            f"🧠 <b>AI Reasoning:</b> <i>{prediction_data['reasoning']}</i>\n\n"
                            f"🔄 <b>Suggested Smart Alternatives:</b>\n"
                            f"{alts_text}\n\n"
                            f"Shall I secure a backup route for you before prices surge?"
                        )

                        keyboard = {
                            "inline_keyboard": [
                                [
                                    {
                                        "text": "🔄 Show Real-time Backups",
                                        "callback_data": f"route_{pnr}",
                                    }
                                ]
                            ]
                        }
                        requests.post(
                            f"https://api.telegram.org/bot{bot_token}/sendMessage",
                            json={
                                "chat_id": chat_id,
                                "text": msg,
                                "parse_mode": "HTML",
                                "reply_markup": keyboard,
                            },
                        )

                        db.bookings.update_one(
                            {"_id": booking["_id"]},
                            {"$set": {"notified_wl_prediction": True}},
                        )

            # -----------------------------------------------------------
            # CHART PREPARATION ENGINE (Triggered 4 Hours / 240 mins before)
            # -----------------------------------------------------------
            if 230 <= diff_minutes <= 245 and not booking.get("notified_chart_prep"):
                status_text = booking.get("status", "").upper()

                if "WL" in status_text or "RAC" in status_text:
                    print(f"🚂 Triggering Chart Preparation for PNR: {pnr}")

                    prediction_data = run_smart_wl_prediction(booking)
                    final_prob = prediction_data.get("adjusted_probability", 0)

                    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
                    chat_id = booking.get("chat_id")

                    import random

                    is_confirmed = False

                    if "RAC" in status_text:
                        is_confirmed = True
                    else:
                        is_confirmed = random.randint(1, 100) <= final_prob

                    if is_confirmed:

                        travel_class = "3A"
                        coach_prefix = (
                            "B"
                            if "3A" in travel_class
                            else "A" if "2A" in travel_class else "S"
                        )
                        new_seat = f"{coach_prefix}{random.randint(1,6)}, Seat {random.randint(1,72)}"

                        msg = (
                            f"🎉 <b>CHART PREPARED - TICKET CONFIRMED!</b>\n\n"
                            f"PNR: <code>{pnr}</code>\n"
                            f"Allocated Berth: <b>{new_seat}</b>\n\n"
                            f"<i>Please pack your bags, your pre-departure cab alert will arrive soon.</i>"
                        )

                        db.bookings.update_one(
                            {"_id": booking["_id"]},
                            {
                                "$set": {
                                    "status": "PAID (Confirmed)",
                                    "seats": f"👤 {passenger_name} - {new_seat}",
                                    "notified_chart_prep": True,
                                }
                            },
                        )
                    else:
                        msg = (
                            f"❌ <b>CHART PREPARED - WAITLIST DROPPED</b>\n\n"
                            f"PNR: <code>{pnr}</code>\n"
                            f"Unfortunately, your waitlisted ticket did not confirm and has been automatically dropped by IRCTC.\n\n"
                            f"The full amount will be refunded to your source account in 3-4 working days."
                        )

                        db.bookings.update_one(
                            {"_id": booking["_id"]},
                            {
                                "$set": {
                                    "status": "Cancelled (Auto-Dropped)",
                                    "notified_chart_prep": True,
                                }
                            },
                        )

                    requests.post(
                        f"https://api.telegram.org/bot{bot_token}/sendMessage",
                        json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"},
                    )

            # -----------------------------------------------------------
            # RULE 1: PRE-DEPARTURE (Cab & Food Alerts)
            # -----------------------------------------------------------

            if is_flight:
                # ✈️ For FLIGHTS: Trigger 3 to 4 hours (180 - 240 mins) before departure
                if 60 <= diff_minutes <= 240:
                    if not booking.get("notified_pre_departure"):
                        print(f"-> ✈️ Firing FLIGHT Pre-Departure for {pnr}")
                        trigger_pre_departure_workflow(chat_id, pnr)
                        db.bookings.update_one(
                            {"_id": booking["_id"]},
                            {"$set": {"notified_pre_departure": True}},
                        )
            else:
                # 🚂 For TRAINS: Trigger 1 to 2 hours (60 - 120 mins) before departure
                if 60 <= diff_minutes <= 120:
                    if not booking.get("notified_pre_departure"):
                        print(f"-> 🚂 Firing TRAIN Pre-Departure for {pnr}")
                        trigger_pre_departure_workflow(chat_id, pnr)
                        db.bookings.update_one(
                            {"_id": booking["_id"]},
                            {"$set": {"notified_pre_departure": True}},
                        )

            # -----------------------------------------------------------
            # 🛑 THE FLIGHT SHIELD: In-transit rules ONLY run for TRAINS
            # -----------------------------------------------------------
            if not is_flight:

                # RULE 2: Post-Boarding Check-In & Shakti (T+20 mins)
                if -25 <= diff_minutes <= -15:
                    if not booking.get("notified_post_boarding"):
                        print(f"-> Firing Post-Boarding for {pnr}")
                        trigger_post_boarding_checkin(chat_id, pnr)

                        if gender == "FEMALE" and is_solo:
                            print(f"-> Firing Project Shakti for {pnr}")
                            trigger_project_shakti_onboarding(
                                chat_id, pnr, passenger_name
                            )

                        db.bookings.update_one(
                            {"_id": booking["_id"]},
                            {"$set": {"notified_post_boarding": True}},
                        )

                # -----------------------------------------------------------
                # RULE 2.5: HOURLY LIVE TRACKING (Every 60 mins after departure)
                # -----------------------------------------------------------
                if diff_minutes < -60:
                    hours_passed = int((-diff_minutes) // 60)
                    last_update_hour = booking.get("last_hourly_update_hour", 0)

                    if hours_passed > last_update_hour:
                        arr_diff_minutes_temp = 999
                        if "arrival_time" in booking:
                            arr_raw = (
                                booking["arrival_time"].replace("Z", "").split("+")[0]
                            )
                            arr_time = datetime.fromisoformat(arr_raw)
                            arr_diff_minutes_temp = (
                                arr_time - current_time
                            ).total_seconds() / 60

                        if arr_diff_minutes_temp > 60:

                            t_num = booking.get("train_number", "UNKNOWN")
                            if t_num == "UNKNOWN":
                                import re

                                journey_str = booking.get("journey", "")
                                t_match = re.search(r"\((\d{5})\)", journey_str)
                                t_num = t_match.group(1) if t_match else "Unknown"

                            raw_dep_f = (
                                booking["departure_time"].replace("Z", "").split("+")[0]
                            )
                            f_date = datetime.fromisoformat(raw_dep_f).strftime(
                                "%Y%m%d"
                            )

                            print(
                                f"-> Firing Hourly Update ({hours_passed} Hour) for {pnr}"
                            )

                            current_delay = trigger_hourly_live_tracking(
                                chat_id, pnr, t_num, f_date
                            )

                            db.bookings.update_one(
                                {"_id": booking["_id"]},
                                {
                                    "$set": {
                                        "last_hourly_update_hour": hours_passed,
                                        "current_delay_minutes": (
                                            current_delay if current_delay else 0
                                        ),
                                    }
                                },
                            )

                # 🚨 SMART ARRIVAL CALCULATION (Dynamic ETA)
                arr_diff_minutes = 999
                if "arrival_time" in booking:
                    arr_raw = booking["arrival_time"].replace("Z", "").split("+")[0]
                    base_arr_time = datetime.fromisoformat(arr_raw)
                    delay_offset = booking.get("current_delay_minutes", 0)
                    effective_arr_time = base_arr_time + timedelta(minutes=delay_offset)
                    arr_diff_minutes = (
                        effective_arr_time - current_time
                    ).total_seconds() / 60

                # -----------------------------------------------------------
                # RULE 3: WAKE-UP CALL & FOOD CHECK (T-30 mins to Smart Arrival)
                # -----------------------------------------------------------
                if 0 < arr_diff_minutes <= 30 and not booking.get("notified_arrival"):
                    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
                    print(
                        f"-> Firing Smart Wake-up for {pnr} (Delay: {booking.get('current_delay_minutes', 0)} mins)"
                    )

                    journey_str = booking.get("journey", "")
                    dest_station = (
                        journey_str.split(" to ")[-1].strip()
                        if " to " in journey_str
                        else "your destination"
                    )

                    msg = (
                        f"🌅 <b>WAKE UP CALL!</b>\n\n"
                        f"Good morning! Your train is just 30 minutes away from {dest_station}.\n\n"
                        f"🧴 Please wake up, freshen up, and double-check your berths to ensure you've packed all your belongings, chargers, and bags.\n\n"
                        f"Shall I book a local transit (Rapido/Cab) to take you from the station to your final destination?"
                    )

                    keyboard = {
                        "inline_keyboard": [
                            [
                                {
                                    "text": "🚕 Yes, Book a Cab",
                                    "callback_data": f"transit_cab_{pnr}",
                                }
                            ],
                            [
                                {
                                    "text": "❌ No, I'm good",
                                    "callback_data": "transit_local",
                                }
                            ],
                        ]
                    }
                    requests.post(
                        f"https://api.telegram.org/bot{bot_token}/sendMessage",
                        json={
                            "chat_id": chat_id,
                            "text": msg,
                            "reply_markup": keyboard,
                            "parse_mode": "HTML",
                        },
                    )
                    db.bookings.update_one(
                        {"_id": booking["_id"]}, {"$set": {"notified_arrival": True}}
                    )

                # -----------------------------------------------------------
                # RULE 4: PRE-ARRIVAL CAB BOOKING (T-10 mins to Smart Arrival)
                # -----------------------------------------------------------
                if 0 < arr_diff_minutes <= 10 and not booking.get("notified_cab"):
                    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
                    print(f"-> Firing Smart Cab Booking for {pnr}")
                    p_name = booking.get("passenger_name", "Passenger")

                    msg = (
                        f"🚖 <b>Destination Approaching!</b>\n\n"
                        f"Hi {p_name}, you will reach your destination in exactly 10 minutes.\n"
                        f"Do you need a ride to your final specific address? Let me know based on your luggage:"
                    )

                    keyboard = {
                        "inline_keyboard": [
                            [
                                {
                                    "text": "🧳 Heavy Luggage (Book Ola Cab)",
                                    "callback_data": f"transit_cab_{pnr}",
                                }
                            ],
                            [
                                {
                                    "text": "🎒 Light Luggage (Book Rapido Bike)",
                                    "callback_data": f"transit_bike_{pnr}",
                                }
                            ],
                            [
                                {
                                    "text": "🚶 I will use Local Transit",
                                    "callback_data": "transit_local",
                                }
                            ],
                        ]
                    }
                    requests.post(
                        f"https://api.telegram.org/bot{bot_token}/sendMessage",
                        json={
                            "chat_id": chat_id,
                            "text": msg,
                            "reply_markup": keyboard,
                            "parse_mode": "HTML",
                        },
                    )
                    db.bookings.update_one(
                        {"_id": booking["_id"]}, {"$set": {"notified_cab": True}}
                    )

            # -----------------------------------------------------------
            # RULE 5: FLIGHT LANDING TRIGGER (Post-Arrival)
            # -----------------------------------------------------------
            if is_flight:
                # 1. 🛬 CALCULATE EXACT ARRIVAL TIME
                arr_diff_minutes = 999
                if "arrival_time" in booking:
                    arr_raw = booking["arrival_time"].replace("Z", "").split("+")[0]
                    arr_time = datetime.fromisoformat(arr_raw)
                    arr_diff_minutes = (arr_time - current_time).total_seconds() / 60

                # 2. 🛬 Trigger exact at Arrival Time or up to 30 mins after
                if -30 <= arr_diff_minutes <= 0 and not booking.get("notified_arrival"):
                    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

                    journey_str = booking.get("journey", "")
                    dest_city = (
                        journey_str.split(" to ")[-1].split("(")[0].strip()
                        if " to " in journey_str
                        else "your destination"
                    )
                    p_name = booking.get("passenger_name", "Passenger")

                    print(f"-> 🛬 Firing FLIGHT Arrival Trigger for {pnr}")

                    msg = (
                        f"🛬 <b>Welcome to {dest_city}, {p_name}!</b>\n\n"
                        f"I hope you had a safe flight. You can turn off your airplane mode now.\n\n"
                        f"Ready to book your stay? Click below to initiate the hotel booking process."
                    )

                    # 🏨 Callback button
                    keyboard = {
                        "inline_keyboard": [
                            [
                                {
                                    "text": "🏨 Proceed to Book Hotel",
                                    "callback_data": f"flight_hotel_{pnr}",
                                }
                            ]
                        ]
                    }

                    requests.post(
                        f"https://api.telegram.org/bot{bot_token}/sendMessage",
                        json={
                            "chat_id": chat_id,
                            "text": msg,
                            "parse_mode": "HTML",
                            "reply_markup": keyboard,
                        },
                    )

                    db.bookings.update_one(
                        {"_id": booking["_id"]}, {"$set": {"notified_arrival": True}}
                    )

    except Exception as e:
        print(f"❌ Autopilot Error: {e}")


# ---------------------------------------------------------
# FASTAPI LIFESPAN (STARTUP/SHUTDOWN)
# ---------------------------------------------------------
scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting Agentra Autopilot System...")
    scheduler.add_job(master_timetable_checker, "interval", minutes=1)
    scheduler.start()
    yield
    print("🛑 Shutting down Agentra Autopilot...")
    scheduler.shutdown()


app = FastAPI(lifespan=lifespan)

user_states = {}
shakti_states = {}


FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/")
def read_root():
    return {"status": "Backend Online"}


@app.on_event("startup")
async def startup_db_client():
    await init_db()


MONGO_URL = os.getenv("MONGO_URI", "mongodb://localhost:27017")
db = MongoClient(MONGO_URL).nexustravel


from fastapi import Header


@app.get("/api/bookings")
async def get_all_bookings(x_user_id: str = Header(None)): 
    try:
      
        if not x_user_id:
            return {"status": "error", "message": "Unauthorized: User ID missing"}

        
        bookings = list(db.bookings.find({"user_id": x_user_id}, {"_id": 0}).sort("timestamp", -1))
        
        return {"status": "success", "data": bookings}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/bookings")
async def create_new_booking(booking: BookingSchema, x_user_id: str = Header(None)): 
    try:
        if not x_user_id:
            return {"status": "error", "message": "Unauthorized: User ID missing"}

        booking_data = booking.model_dump()
        
        
        booking_data["user_id"] = x_user_id 
        
        booking_data["departure_time"] = booking_data["departure_time"].isoformat()
        booking_data["arrival_time"] = booking_data["arrival_time"].isoformat()
        booking_data["timestamp"] = datetime.now().isoformat()

        total_amount = sum(item["cost"] for item in booking_data.get("expenses", []))
        booking_data["total_amount"] = total_amount

        result = db.bookings.insert_one(booking_data)
        return {
            "status": "success",
            "message": "Booking Saved!",
            "id": str(result.inserted_id),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ---------------------------------------------------------
# EVENT-DRIVEN ORCHESTRATION ENDPOINTS
# ---------------------------------------------------------
@app.post("/api/test-pre-departure")
async def test_pre_departure(background_tasks: BackgroundTasks, chat_id: str = "YOUR_TELEGRAM_CHAT_ID"):
    background_tasks.add_task(trigger_pre_departure_workflow, chat_id)
    return {"status": "Triggered background chart prep and live tracking."}

@app.post("/api/test-post-boarding")
async def test_post_boarding(background_tasks: BackgroundTasks, chat_id: str = "YOUR_CHAT_ID"):
    background_tasks.add_task(trigger_post_boarding_checkin, chat_id, "9286761423")
    return {"status": "Triggered"}

@app.post("/api/test-hourly-update")
async def test_hourly_update(background_tasks: BackgroundTasks, chat_id: str = "YOUR_CHAT_ID"):
    background_tasks.add_task(trigger_hourly_live_tracking, chat_id, "9286761423", "12004")
    return {"status": "Triggered"}


@app.post("/api/test-wake-up")
async def test_wake_up(background_tasks: BackgroundTasks, chat_id: str = "YOUR_CHAT_ID"):
    background_tasks.add_task(trigger_wake_up_call, chat_id, "9286761423")
    return {"status": "Triggered"}

@app.post("/api/test-shakti")
async def test_shakti(background_tasks: BackgroundTasks, chat_id: str = "YOUR_CHAT_ID"):
    background_tasks.add_task(trigger_project_shakti_onboarding, chat_id, "9286761423", "Priya")
    return {"status": "Triggered Shakti Workflow"}

def send_real_sms(phone_number: str, message: str):
    """Sends a real SMS using Fast2SMS API"""
    url = "https://www.fast2sms.com/dev/bulkV2"
    querystring = {
        "authorization": os.getenv("FAST2SMS_API_KEY"),
        "message": message,
        "language": "english",
        "route": "q",
        "numbers": phone_number,
    }
    headers = {"cache-control": "no-cache"}
    try:
        response = requests.request("GET", url, headers=headers, params=querystring)
        if response.status_code == 200:
            print(f"✅ Real SMS API Hit successfully for {phone_number}")
    except Exception as e:
        print("❌ SMS Failed:", e)


import re

#  DYNAMIC LIVE TRACKER ENGINE (PROJECT SHAKTI)
import asyncio
import os
import requests
import re
from datetime import datetime
from services.railway_api import get_live_train_status


# API-POWERED HOURLY LIVE TRACKING
def trigger_hourly_live_tracking(
    chat_id: str, pnr: str, train_number: str, formatted_date: str
):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

    live_data = get_live_train_status(train_number, formatted_date)

    current_station = "En route"
    delay_text = "Tracking..."
    status_msg = "Live tracking active."
    final_dest = "Destination"
    final_eta = "N/A"
    delay_mins = 0

    if live_data and "body" in live_data:
        data_body = live_data["body"]
        status_msg = data_body.get("train_status_message", status_msg)
        current_station_code = data_body.get("current_station", "")
        stations_list = data_body.get("stations", [])

        if stations_list:
            last_stn = stations_list[-1]
            final_dest = last_stn.get("stationName", "Destination")
            final_eta = last_stn.get(
                "actual_arrival_time", last_stn.get("arrivalTime", "N/A")
            )

            for stn in stations_list:
                if stn.get("stationCode") == current_station_code:
                    sch_time = stn.get("departureTime", stn.get("arrivalTime", ""))
                    act_time = stn.get(
                        "actual_departure_time", stn.get("actual_arrival_time", "")
                    )

                    if sch_time and act_time and ":" in sch_time and ":" in act_time:
                        try:
                            sh, sm = map(int, sch_time.split(":"))
                            ah, am = map(int, act_time.split(":"))
                            sch_total = sh * 60 + sm
                            act_total = ah * 60 + am
                            diff = act_total - sch_total

                            if diff < -720:
                                diff += 1440
                            delay_mins = diff
                        except Exception as e:
                            print(f"Time math error: {e}")
                    break

        if delay_mins > 0:
            delay_text = f"🔴 Delayed by {delay_mins} mins"
        elif delay_mins < 0:
            delay_text = f"🟢 Early by {abs(delay_mins)} mins"
        else:
            delay_text = "🟢 Running On Time"

    msg = (
        f"📡 <b>Live Hourly Update (Train {train_number})</b>\n\n"
        f"📍 <b>Latest Status:</b> {status_msg}\n"
        f"⏱️ <b>Punctuality:</b> {delay_text}\n"
        f"🏁 <b>Destination:</b> {final_dest} (ETA: {final_eta})\n\n"
        f"<i>Sleep tight! I'm keeping an eye on the route and will wake you up 30 mins before arrival.</i>"
    )

    requests.post(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"},
    )

    return delay_mins


# DYNAMIC LIVE TRACKER ENGINE (ENRICHED PROJECT SHAKTI)
async def execute_shakti_live_tracker(
    chat_id: str, message_id: int, booking_data: dict
):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    base_url = f"https://api.telegram.org/bot{bot_token}/editMessageText"

    pnr = booking_data.get("pnr", "UNKNOWN") if booking_data else "UNKNOWN"
    p_name = (
        booking_data.get("passenger_name", "Passenger") if booking_data else "Passenger"
    )
    journey = (
        booking_data.get("journey", "Unknown Route")
        if booking_data
        else "Unknown Route"
    )
    seats = (
        booking_data.get("seats", "Unassigned Seat")
        if booking_data
        else "Unassigned Seat"
    )

    train_number = booking_data.get("train_number", "UNKNOWN")

    if train_number == "UNKNOWN":
        import re

        train_no_match = re.search(r"\((\d{5})\)", journey)
        train_number = train_no_match.group(1) if train_no_match else "11108"
    train_name = journey.split(" from ")[0].strip() if " from " in journey else journey

    formatted_date = booking_data.get(
        "train_origin_date", datetime.now().strftime("%Y%m%d")
    )

    current_station = "En route (GPS locating...)"
    next_station = "Next Upcoming Station"
    eta_next = "Calculating..."
    speed = "Tracking Active"
    status_msg = "Live tracking active."

    # Make the RapidAPI Call
    if train_number and train_number != "Unknown":
        live_data = get_live_train_status(train_number, formatted_date)

        if live_data and "body" in live_data:
            data_body = live_data["body"]

            status_msg = data_body.get("train_status_message", status_msg)

            current_station_code = data_body.get("current_station", "")
            stations_list = data_body.get("stations", [])

            for i, stn in enumerate(stations_list):
                if stn.get("stationCode") == current_station_code:
                    current_station = stn.get("stationName", current_station_code)

                    if i + 1 < len(stations_list):
                        next_stn = stations_list[i + 1]
                        next_station = next_stn.get("stationName", "Next Station")

                        eta_next = next_stn.get(
                            "actual_arrival_time", next_stn.get("arrivalTime", "N/A")
                        )
                    break

    # --- UI & ESCALATION LOGIC (Countdown) ---
    if message_id != 0:
        for i in range(20, 0, -5):
            if shakti_states.get(chat_id) == "CANCELLED":
                return
            if shakti_states.get(chat_id) == "CONFIRMED":
                break

            countdown_msg = (
                f"⚠️ <b>SHAKTI SHIELD INITIATED</b> ⚠️\n\n"
                f"Are you safe, {p_name}? If I don't receive a response in <b>{i} seconds</b>, "
                f"I will auto-escalate this to RPF and your Emergency Contacts."
            )
            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "🚨 YES, I NEED HELP NOW",
                            "callback_data": "shakti_confirm",
                        }
                    ],
                    [
                        {
                            "text": "❌ False Alarm (Cancel)",
                            "callback_data": "shakti_cancel",
                        }
                    ],
                ]
            }
            requests.post(
                base_url,
                json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "text": countdown_msg,
                    "parse_mode": "HTML",
                    "reply_markup": keyboard,
                },
            )
            await asyncio.sleep(5)

        if shakti_states.get(chat_id) == "CANCELLED":
            return

    shakti_states[chat_id] = "ESCALATING"

    # ENRICHED EMERGENCY FAMILY ALERT
    emergency_chat_id = os.getenv("EMERGENCY_CHAT_ID")
    family_alert_msg = (
        f"🚨 <b>URGENT: SOS DISTRESS SIGNAL (PROJECT SHAKTI)</b> 🚨\n\n"
        f"<b>Passenger {p_name}</b> has triggered an emergency alarm from the train.\n\n"
        f"📋 <b>JOURNEY DETAILS:</b>\n"
        f"• <b>Passenger:</b> {p_name} (Solo Female Traveler)\n"
        f"• <b>Train:</b> {train_name} ({train_number})\n"
        f"• <b>PNR:</b> <code>{pnr}</code>\n"
        f"• <b>Exact Seat:</b> {seats}\n\n"
        f"📡 <b>LIVE TRACKING DATA:</b>\n"
        f"• <b>Last Update:</b> {status_msg}\n"
        f"• <b>Crossed Station:</b> {current_station}\n"
        f"• <b>Next Stop:</b> {next_station} (ETA: {eta_next})\n\n"
        f"🚓 <b>ACTION TAKEN:</b>\n"
        f"Incident auto-escalated to RPF Cyber Control. Escort team dispatched to the coach at {next_station}.\n\n"
        f"📞 <i>Please attempt to contact {p_name} immediately!</i>"
    )

    # Send to Emergency Chat Group
    if emergency_chat_id:
        requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={
                "chat_id": emergency_chat_id,
                "text": family_alert_msg,
                "parse_mode": "HTML",
            },
        )

    target_sms_number = "7974711962"
    dynamic_sms_text = f"EMERGENCY! {p_name} triggered SOS on PNR {pnr} ({train_number}). Seat: {seats}. Location: Near {current_station}. RPF dispatched. Contact immediately."

    try:
        send_real_sms(target_sms_number, dynamic_sms_text)
    except Exception as e:
        print(f"SMS failed in Shakti: {e}")

    # ENRICHED USER SIMULATION (What Shreya sees on her phone)
    if message_id != 0:
        simulation_steps = [
            f"🟡 <b>T+0s:</b> Locking GPS Coordinates & Seat Info ({seats})...",
            f"🟠 <b>T+4s:</b> Formulating Distress Payload...\n👉 SMS/Telegram dispatched to Emergency Contacts with live tracking ({current_station}).",
            f"🔵 <b>T+8s:</b> Transmitting Zero-FIR to RPF Control Room (Train {train_number})...",
            f"🟢 <b>T+12s: ESCALATION COMPLETE.</b>\n\n🚓 Ticket #EMG-8821 Assigned.\n👮 RPF Escort is boarding the coach at <b>{next_station}</b> in {eta_next}.\n\n<i>Stay calm, {p_name}. Help is arriving at your berth. Do not confront anyone.</i>",
        ]

        current_text = "🚨 <b>SHAKTI ESCALATION PROTOCOL ACTIVE</b> 🚨\n\n"

        for step in simulation_steps:
            current_text += f"{step}\n"
            requests.post(
                base_url,
                json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "text": current_text,
                    "parse_mode": "HTML",
                },
            )
            await asyncio.sleep(4)
    else:
        # Offline SMS handling logic
        requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": "✅ Offline SOS processed successfully. RPF dispatched to next station.",
                "parse_mode": "HTML",
            },
        )


# THEFT PROTOCOL LIVE SIMULATION
import re
import asyncio
import requests
import os


async def execute_theft_live_tracker(
    new_chat_id: str, message_id: int, booking_data: dict
):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    base_url = f"https://api.telegram.org/bot{bot_token}/editMessageText"

    pnr = booking_data.get("pnr", "UNKNOWN")
    p_name = booking_data.get("passenger_name", "Passenger")
    seats = booking_data.get("seats", "Unassigned Seat")

    train_number = booking_data.get("train_number", "UNKNOWN")
    if train_number == "UNKNOWN":
        import re

        journey_text = booking_data.get("journey", "")
        train_no_match = re.search(r"\((\d{5})\)", journey_text)
        train_number = train_no_match.group(1) if train_no_match else "11108"

    formatted_date = booking_data.get(
        "train_origin_date", datetime.now().strftime("%Y%m%d")
    )

    current_station = "En route (GPS locating...)"
    next_station = "Next Upcoming Station"
    eta_next = "Calculating..."
    status_msg = "Live tracking active."

    try:

        if train_number and train_number != "Unknown":
            live_data = get_live_train_status(train_number, formatted_date)

            if live_data and "body" in live_data:
                data_body = live_data["body"]
                status_msg = data_body.get("train_status_message", status_msg)

                current_station_code = data_body.get("current_station", "")
                stations_list = data_body.get("stations", [])

                for i, stn in enumerate(stations_list):
                    if stn.get("stationCode") == current_station_code:
                        current_station = stn.get("stationName", current_station_code)
                        if i + 1 < len(stations_list):
                            next_stn = stations_list[i + 1]
                            next_station = next_stn.get("stationName", "Next Station")
                            eta_next = next_stn.get(
                                "actual_arrival_time",
                                next_stn.get("arrivalTime", "N/A"),
                            )
                        break
    except Exception as e:
        print(f"Tracking API Error in Theft Protocol: {e}")
        status_msg = "Live tracking currently degraded."

    emergency_chat_id = os.getenv("EMERGENCY_CHAT_ID")

    # DYNAMIC ALERT FOR EMERGENCY CONTACT
    family_alert_msg = (
        f"🚨 <b>CRITICAL SECURITY ALERT: DEVICE COMPROMISED</b> 🚨\n\n"
        f"<b>{p_name}'s</b> phone has been reported STOLEN on the train.\n\n"
        f"🎫 <b>PNR:</b> <code>{pnr}</code>\n"
        f"💺 <b>Seat:</b> {seats}\n\n"
        f"📡 <b>LIVE TRACKING DATA:</b>\n"
        f"• <b>Status:</b> {status_msg}\n"
        f"• <b>Current/Crossed:</b> {current_station}\n"
        f"• <b>Approaching:</b> {next_station} at {eta_next}\n\n"
        f"⚠️ <b>DO NOT</b> reply to any messages, calls, or UPI requests from {p_name}'s number.\n"
        f"🚓 An official Zero-FIR has been lodged and RPF is boarding at {next_station}."
    )

    if emergency_chat_id:
        requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={
                "chat_id": emergency_chat_id,
                "text": family_alert_msg,
                "parse_mode": "HTML",
            },
        )

    # 📱 SMS TRIGGER
    target_sms_number = "7974711962"
    sms_text = f"URGENT: {p_name}'s phone STOLEN (PNR {pnr}). Cross: {current_station}. Next: {next_station} at {eta_next}. RPF informed."
    try:
        send_real_sms(target_sms_number, sms_text)
    except Exception:
        pass

    simulation_steps = [
        f"🟡 <b>T+0s:</b> Verifying Override Code...\nIdentity confirmed as {p_name}.",
        f"🟠 <b>T+4s:</b> Engaging SHAKTI Protocol. Fetching Train {train_number} coordinates...\n📍 <i>{status_msg}</i>",
        f"🔵 <b>T+8s:</b> Broadcasting 'COMPROMISED DEVICE' warning with live coordinates ({current_station} ➡️ {next_station}) to Emergency Contacts.",
        "🟣 <b>T+12s:</b> Auto-Drafting Zero-FIR (Theft) to Railway Protection Force Cyber Cell...",
        f"🟢 <b>T+16s: PROTOCOL COMPLETE.</b>\n\n🚓 GRP Squad has been dispatched to {seats} at {next_station} ({eta_next}).\n🔒 Note: Your Agentra account on the stolen device is now locked out.",
    ]

    current_text = "🚨 <b>ANTI-THEFT OVERRIDE PROTOCOL ACTIVE</b> 🚨\n\n"

    for step in simulation_steps:
        current_text += f"{step}\n\n"
        requests.post(
            base_url,
            json={
                "chat_id": new_chat_id,
                "message_id": message_id,
                "text": current_text,
                "parse_mode": "HTML",
            },
        )
        await asyncio.sleep(4)


# ---------------------------------------------------------
# 🚨 OFFLINE SMS SOS WEBHOOK
# ---------------------------------------------------------
@app.post("/api/sms-webhook")
async def offline_sms_handler(
    background_tasks: BackgroundTasks, From: str = Form(...), Body: str = Form(...)
):
    print(f"📥 Received Offline SMS from {From}: {Body}")
    sms_text = Body.strip().upper()

    if sms_text.startswith("SOS"):
        parts = sms_text.split()
        if len(parts) >= 2:
            pnr = parts[1]
            booking = db.bookings.find_one(
                {"pnr": pnr, "status": "Confirmed & Paid"}, sort=[("timestamp", -1)]
            )

            if booking:
                chat_id = booking.get("chat_id")
                print(f"🚨 OFFLINE SOS TRIGGERED FOR PNR {pnr}")
                background_tasks.add_task(
                    execute_shakti_live_tracker, str(chat_id), 0, booking
                )
                return Response(
                    content='<?xml version="1.0" encoding="UTF-8"?><Response><Message>OFFLINE SOS RECEIVED. RPF dispatched to your seat.</Message></Response>',
                    media_type="application/xml",
                )
    return {"status": "ignored"}


@app.post("/api/telegram-webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

    if "message" in data and "text" in data["message"]:
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        user_text = msg["text"].strip().upper()

        if user_text.startswith("AGENTRA OVERRIDE"):
            parts = user_text.split()
            if len(parts) == 3:
                override_pnr = parts[2].strip()

                print(f"-> EMERGENCY OVERRIDE INITIATED FOR PNR: '{override_pnr}'")

                stolen_booking = db.bookings.find_one(
                    {"pnr": override_pnr}, sort=[("timestamp", -1)]
                )

                if stolen_booking:
                    print("-> PNR Found in DB! Sending Auth Message.")
                    p_name = stolen_booking.get("passenger_name", "Passenger")
                    auth_msg = (
                        f"🛡️ <b>AGENTRA OVERRIDE AUTHENTICATED</b> 🛡️\n\n"
                        f"Welcome back, {p_name}. I noticed you are logging in from a new device/Telegram account.\n"
                        f"Is everything alright?"
                    )
                    auth_keyboard = {
                        "inline_keyboard": [
                            [
                                {
                                    "text": "🚨 MY PHONE IS STOLEN!",
                                    "callback_data": f"theft_confirm_{override_pnr}",
                                }
                            ],
                            [
                                {
                                    "text": "✅ I'm fine, just changing phones.",
                                    "callback_data": "theft_cancel",
                                }
                            ],
                        ]
                    }
                    requests.post(
                        f"https://api.telegram.org/bot{bot_token}/sendMessage",
                        json={
                            "chat_id": chat_id,
                            "text": auth_msg,
                            "parse_mode": "HTML",
                            "reply_markup": auth_keyboard,
                        },
                    )
                else:
                    print("-> ERROR: PNR Not Found in DB!")
                    requests.post(
                        f"https://api.telegram.org/bot{bot_token}/sendMessage",
                        json={
                            "chat_id": chat_id,
                            "text": "❌ Override Failed: Invalid PNR or No Active Journey Found.",
                        },
                    )
            return {"status": "override_checked"}

        if "SHAKTI SOS" in user_text:
            shakti_states[chat_id] = "COUNTDOWN"

            user_booking = db.bookings.find_one(
                {
                    "chat_id": str(chat_id),
                    "status": {"$regex": "Paid", "$options": "i"},
                    "flight_number": "N/A",
                },
                sort=[("timestamp", -1)],
            )

            if not user_booking:
                requests.post(
                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": "No active train journey found for SHAKTI SOS.",
                    },
                )
                return {"status": "no_active_train"}

            initial_msg = (
                "⚠️ <b>SHAKTI SHIELD INITIATED</b> ⚠️\nInitializing countdown..."
            )
            response = requests.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": initial_msg, "parse_mode": "HTML"},
            )

            message_id = response.json()["result"]["message_id"]
            asyncio.create_task(
                execute_shakti_live_tracker(chat_id, message_id, user_booking)
            )
            return {"status": "shakti_countdown_started"}

        elif "EMERGENCY SOS" in user_text:
            sos_menu = (
                f"⚠️ <b>EMERGENCY PROTOCOL INITIATED</b>\n"
                f"I am locking your GPS coordinates. What kind of emergency are you facing?"
            )
            sos_keyboard = {
                "inline_keyboard": [
                    [{"text": "🚑 Medical Emergency", "callback_data": "sos_medical"}],
                    [{"text": "🚓 Theft / Robbery", "callback_data": "sos_theft"}],
                    [
                        {
                            "text": "🛑 Harassment / Misbehavior",
                            "callback_data": "sos_harassment",
                        }
                    ],
                    [
                        {
                            "text": "🧹 Coach Issue (Water/Cleaning)",
                            "callback_data": "sos_cleaning",
                        }
                    ],
                ]
            }
            requests.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": sos_menu,
                    "parse_mode": "HTML",
                    "reply_markup": sos_keyboard,
                },
            )
            return {"status": "sos_menu_sent"}

        # INVOICE: CAB CONFIRMED - Saving cost to DB
        if user_states.get(chat_id) and user_states[chat_id].startswith(
            "waiting_for_address_"
        ):
            state = user_states[chat_id]
            pnr = state.split("_")[-1]
            ride_type = state.split("_")[-2]
            user_states[chat_id] = None
            drop_address = user_text

            # Simulated Cab Cost
            cab_cost = random.randint(150, 450)

            booking_confirm_msg = (
                f"✅ <b>Ride Confirmed!</b>\n\n"
                f"🚖 <b>Type:</b> {ride_type}\n"
                f"📍 <b>Drop Address:</b> {drop_address}\n"
                f"💵 <b>Estimated Fare:</b> ₹{cab_cost}\n\n"
                f"I have synced this with your train's live arrival time. The driver will be waiting exactly outside the station exit. Driver details will be sent via SMS shortly."
            )
            requests.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": booking_confirm_msg,
                    "parse_mode": "HTML",
                },
            )

            # Pushing expense to DB
            db.bookings.update_one(
                {"pnr": pnr},
                {
                    "$push": {
                        "expenses": {
                            "item_id": f"CAB_{random.randint(100,999)}",
                            "expense_type": "CAB",
                            "description": f"{ride_type} to {drop_address}",
                            "cost": cab_cost,
                            "status": "BOOKED",
                            "timestamp": datetime.now(),
                        }
                    },
                    "$inc": {"total_amount": cab_cost},
                    "$set": {"trip_phase": "AWAITING_ACCOMMODATION"},
                },
            )
            return {"status": "ok"}

        # INVOICE: FOOD CONFIRMED - Saving cost to DB
        if user_states.get(chat_id) and str(user_states[chat_id]).startswith(
            "waiting_for_food_"
        ):
            pnr = user_states[chat_id].split("_")[3]
            user_states[chat_id] = None

            food_cost = random.randint(200, 500)

            food_confirm_msg = (
                f"✅ <b>Order Placed Successfully!</b>\n"
                f"Your request for <b>{user_text}</b> has been scheduled via IRCTC E-Catering.\n"
                f"🚆 It will be delivered piping hot to your confirmed seat.\n"
                f"💵 <b>Total: ₹{food_cost}</b> (Cash on Delivery). Bon Appétit!"
            )
            requests.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": food_confirm_msg,
                    "parse_mode": "HTML",
                },
            )

            db.bookings.update_one(
                {"pnr": pnr},
                {
                    "$push": {
                        "expenses": {
                            "item_id": f"FOOD_{random.randint(100,999)}",
                            "expense_type": "FOOD",
                            "description": user_text,
                            "cost": food_cost,
                            "status": "BOOKED",
                            "timestamp": datetime.now().isoformat(),
                        }
                    },
                    "$inc": {"total_amount": food_cost},
                },
            )
            return {"status": "ok"}

    # Telegram Callbacks (Buttons)
    if "callback_query" in data:
        callback_query = data["callback_query"]
        chat_id = callback_query["message"]["chat"]["id"]
        callback_data = callback_query["data"]
        message_id = callback_query["message"]["message_id"]
        callback_id = callback_query["id"]

        requests.post(
            f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery",
            json={"callback_query_id": callback_id},
        )

        if callback_data.startswith("activate_shakti_"):
            requests.post(
                f"https://api.telegram.org/bot{bot_token}/editMessageReplyMarkup",
                json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "reply_markup": {"inline_keyboard": []},
                },
            )
            activation_msg = (
                f"✅ <b>Shakti Shield Activated!</b>\n\n"
                f"I am now actively guarding your PNR routing.\n"
                f"🤫 <b>Your Secret Keyword is:</b> <code>SHAKTI SOS</code>\n\n"
                f"If you are ever in a situation where you cannot click buttons or talk, just type <b>SHAKTI SOS</b> in this chat. I will instantly lock your location and dispatch RPF to your exact berth."
            )
            requests.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": activation_msg, "parse_mode": "HTML"},
            )

        elif callback_data == "shakti_cancel":
            shakti_states[chat_id] = "CANCELLED"
            requests.post(
                f"https://api.telegram.org/bot{bot_token}/editMessageText",
                json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "text": "✅ <b>Shakti Protocol Aborted.</b>\nStay safe! Let me know if you need anything else.",
                    "parse_mode": "HTML",
                },
            )

        elif callback_data == "shakti_confirm":
            shakti_states[chat_id] = "CONFIRMED"
            requests.post(
                f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery",
                json={
                    "callback_query_id": callback_id,
                    "text": "Escalating Immediately!",
                },
            )

        elif callback_data.startswith("sos_"):
            requests.post(
                f"https://api.telegram.org/bot{bot_token}/editMessageReplyMarkup",
                json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "reply_markup": {"inline_keyboard": []},
                },
            )

            category = callback_data.split("_")[1].upper()
            action_text = ""
            if category == "MEDICAL":
                action_text = "The Station Medical Officer and an Ambulance have been placed on standby at the upcoming station."
            elif category == "THEFT":
                action_text = "A digital Zero-FIR draft has been generated. GRP squad is waiting at the next platform."
            elif category == "HARASSMENT":
                action_text = "The On-Duty TTE and Train Escort RPF team have been summoned to your coach immediately."
            elif category == "CLEANING":
                action_text = "An automated OBHS ticket has been raised. Cleaning staff is en route to your coach."

            sos_confirm = (
                f"✅ <b>REPORT LOGGED & ESCALATED</b>\n\n"
                f"<b>Category:</b> {category}\n"
                f"<b>Action Taken:</b> {action_text}\n\n"
                f"Please stay calm. Agentra is managing the logistics for you."
            )
            requests.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": sos_confirm, "parse_mode": "HTML"},
            )

        elif callback_data == "theft_cancel":
            requests.post(
                f"https://api.telegram.org/bot{bot_token}/editMessageText",
                json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "text": "✅ <b>Override Logged.</b> Happy to know you are safe. Your new device is now linked to your journey.",
                    "parse_mode": "HTML",
                },
            )

        elif callback_data.startswith("theft_confirm_"):
            override_pnr = callback_data.split("_")[2]
            stolen_booking = db.bookings.find_one({"pnr": override_pnr})

            requests.post(
                f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery",
                json={
                    "callback_query_id": callback_id,
                    "text": "Initiating Anti-Theft Protocol!",
                },
            )
            requests.post(
                f"https://api.telegram.org/bot{bot_token}/editMessageReplyMarkup",
                json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "reply_markup": {"inline_keyboard": []},
                },
            )

            asyncio.create_task(
                execute_theft_live_tracker(chat_id, message_id, stolen_booking)
            )

        elif callback_data.startswith("book_cab_"):
            pnr = callback_data.split("_")[2]  # 🚨 PNR BUTTON SE NIKALA
            requests.post(
                f"https://api.telegram.org/bot{bot_token}/editMessageReplyMarkup",
                json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "reply_markup": {"inline_keyboard": []},
                },
            )
            cab_msg = (
                f"✅ <b>Cab Request Initiated!</b>\n"
                f"A local partner (Rapido/Ola) is being routed to your current GPS location.\n"
                f"🚘 Vehicle details will be SMSed to your registered mobile number shortly.\n"
                f"💵 You can pay the driver directly via Cash/UPI upon reaching the station. Safe travels!"
            )
            requests.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": cab_msg, "parse_mode": "HTML"},
            )

            cab_cost = random.randint(150, 350)
            db.bookings.update_one(
                {"pnr": pnr},
                {
                    "$push": {
                        "expenses": {
                            "item_id": f"CAB_{random.randint(100,999)}",
                            "expense_type": "CAB",
                            "description": "Rapido/Ola Station Pickup",
                            "cost": cab_cost,
                            "status": "BOOKED",
                            "timestamp": datetime.now().isoformat(),
                        }
                    },
                    "$inc": {"total_amount": cab_cost},
                },
            )

        elif callback_data == "ignore_cab":
            requests.post(
                f"https://api.telegram.org/bot{bot_token}/editMessageReplyMarkup",
                json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "reply_markup": {"inline_keyboard": []},
                },
            )
            requests.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": "Got it! Have a safe journey to the station.",
                },
            )

        elif callback_data.startswith("book_arrival_cab_"):
            pnr = callback_data.split("_")[3]
            requests.post(
                f"[https://api.telegram.org/bot](https://api.telegram.org/bot){bot_token}/editMessageReplyMarkup",
                json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "reply_markup": {"inline_keyboard": []},
                },
            )

            confirmation_msg = (
                f"✅ <b>Cab Confirmed!</b>\n\n"
                f"🚕 <b>Driver:</b> Ramesh Kumar\n"
                f"⭐ <b>Rating:</b> 4.8\n"
                f"🔢 <b>Vehicle:</b> UP 70 AB 1234 (Swift Dzire)\n"
                f"📍 <b>Pickup:</b> Railway Station Main Exit\n"
                f"💳 <b>Estimated Fare:</b> ₹250 (Added to your trip expenses)\n\n"
                f"<i>The driver will wait for you outside the station. Safe onward journey!</i>"
            )

            requests.post(
                f"[https://api.telegram.org/bot](https://api.telegram.org/bot){bot_token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": confirmation_msg,
                    "parse_mode": "HTML",
                },
            )

            cab_cost = 250.0
            db.bookings.update_one(
                {"pnr": pnr},
                {
                    "$push": {
                        "expenses": {
                            "item_id": f"CAB_ARR_{random.randint(100,999)}",
                            "expense_type": "LOCAL_TRANSIT",
                            "description": "Pre-Arrival Station Pickup Cab",
                            "cost": cab_cost,
                            "status": "PAID",
                            "timestamp": datetime.now().isoformat(),
                        }
                    },
                    "$inc": {"total_amount": cab_cost},
                },
            )

        elif callback_data == "ignore_arrival_cab":
            requests.post(
                f"[https://api.telegram.org/bot](https://api.telegram.org/bot){bot_token}/editMessageReplyMarkup",
                json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "reply_markup": {"inline_keyboard": []},
                },
            )
            requests.post(
                f"[https://api.telegram.org/bot](https://api.telegram.org/bot){bot_token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": "Got it! Have a safe onward journey. You can check local transit options outside the station.",
                },
            )

        # ---------------------------------------------------------
        # FLIGHT HOTEL BOOKING TRIGGER
        # ---------------------------------------------------------

        elif callback_data.startswith("flight_hotel_"):

            pnr = callback_data.split("_")[2]

            bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

            # 1. Update DB to trigger your React UI Shield

            db.bookings.update_one(
                {"pnr": pnr}, {"$set": {"trip_phase": "AWAITING_ACCOMMODATION"}}
            )

            # 2. Update Telegram Message & Remove Button

            success_msg = (
                f"✅ <b>Accommodation Module Unlocked!</b>\n\n"
                f"Your trip (PNR: {pnr}) is now ready for hotel booking.\n\n"
                f"👉 <i>Please checkout the Agentra Dashboard on your browser to view options and lock your room!</i>"
            )

            requests.post(
                f"https://api.telegram.org/bot{bot_token}/editMessageText",
                json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "text": success_msg,
                    "parse_mode": "HTML",
                },
            )

            # Popup feedback

            requests.post(
                f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery",
                json={"callback_query_id": callback_id, "text": "Dashboard Unlocked!"},
            )

        elif callback_data.startswith("transit_cab_") or callback_data.startswith(
            "transit_bike_"
        ):
            pnr = callback_data.split("_")[-1]
            ride_type = "Cab" if "cab" in callback_data else "Rapido Bike"
            requests.post(
                f"https://api.telegram.org/bot{bot_token}/editMessageReplyMarkup",
                json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "reply_markup": {"inline_keyboard": []},
                },
            )
            user_states[chat_id] = f"waiting_for_address_{ride_type}_{pnr}"
            requests.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": f"🗺️ Great! Where exactly do you want to go? (Please type your drop location for the {ride_type}):",
                },
            )

        elif callback_data == "transit_local":
            requests.post(
                f"https://api.telegram.org/bot{bot_token}/editMessageReplyMarkup",
                json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "reply_markup": {"inline_keyboard": []},
                },
            )
            requests.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": "Got it! Have a safe onward journey. You can check local bus/metro routes outside the station.",
                },
            )

        # INVOICE: USUAL FOOD (MASALA DOSA) - Saving cost to DB
        elif callback_data.startswith("food_usual_"):
            pnr = callback_data.split("_")[2]
            requests.post(
                f"https://api.telegram.org/bot{bot_token}/editMessageReplyMarkup",
                json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "reply_markup": {"inline_keyboard": []},
                },
            )

            dosa_cost = 150
            food_confirm_msg = (
                f"✅ <b>Order Placed Successfully!</b>\n"
                f"Your favorite Masala Dosa has been scheduled via IRCTC E-Catering.\n"
                f"🚆 It will be delivered piping hot to your confirmed seat.\n"
                f"💵 <b>Total: ₹{dosa_cost}</b> (Cash on Delivery). Bon Appétit!"
            )
            requests.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": food_confirm_msg,
                    "parse_mode": "HTML",
                },
            )

            db.bookings.update_one(
                {"pnr": pnr},
                {
                    "$push": {
                        "expenses": {
                            "item_id": f"FOOD_{random.randint(100,999)}",
                            "expense_type": "FOOD",
                            "description": "Masala Dosa",
                            "cost": dosa_cost,
                            "status": "BOOKED",
                            "timestamp": datetime.now().isoformat(),
                        }
                    },
                    "$inc": {"total_amount": dosa_cost},
                },
            )

        elif callback_data.startswith("food_custom_"):
            pnr = callback_data.split("_")[2]
            requests.post(
                f"https://api.telegram.org/bot{bot_token}/editMessageReplyMarkup",
                json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "reply_markup": {"inline_keyboard": []},
                },
            )

            user_states[chat_id] = f"waiting_for_food_{pnr}"
            force_reply_payload = {
                "chat_id": chat_id,
                "text": "🍽️ What would you like to order? (Type your food choice below):",
            }
            requests.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json=force_reply_payload,
            )

        elif callback_data == "food_no":
            requests.post(
                f"https://api.telegram.org/bot{bot_token}/editMessageReplyMarkup",
                json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "reply_markup": {"inline_keyboard": []},
                },
            )
            requests.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": "No worries! Have a safe and happy journey.",
                },
            )

        elif callback_data == "ack_settled":
            requests.post(
                f"https://api.telegram.org/bot{bot_token}/editMessageReplyMarkup",
                json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "reply_markup": {"inline_keyboard": []},
                },
            )
            requests.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": "Awesome! Have a wonderful and safe journey. Agentra is always on guard. 🛡️",
                },
            )

    return {"status": "ok"}


# ---------------------------------------------------------
# 🏨 STAY CONFIRMATION ENDPOINT (WITH INVOICE TRIGGER)
# ---------------------------------------------------------
class BookStayRequest(BaseModel):
    pnr: str
    option_id: str
    option_name: str
    price: int
    passengers: List[Dict] = []


@app.post("/api/accommodations/book")
async def book_accommodation(req: BookStayRequest, x_user_id: str = Header(None)): # 👈 Added Header
    if not x_user_id:
        return {"status": "error", "message": "Unauthorized"}

    if not req.pnr or req.pnr == "CAB9998887":
        real_booking = db.bookings.find_one(
            {
                "user_id": x_user_id, # 👈 Added Filter
                "status": {"$regex": "Paid", "$options": "i"},
                "trip_phase": "AWAITING_ACCOMMODATION",
            }
        )
        if real_booking:
            req.pnr = real_booking["pnr"]

    booking = db.bookings.find_one({"pnr": req.pnr, "user_id": x_user_id}) # 👈 Added Filter
    chat_id = booking.get("chat_id") if booking else os.getenv("EMERGENCY_CHAT_ID")

    stay_booking_id = f"STAY-{random.randint(10000, 99999)}"
    room_no = f"{random.randint(1, 5)}0{random.randint(1, 9)}"

    hotel_data = {
        "stay_booking_id": stay_booking_id,
        "hotel_name": req.option_name,
        "room_no": room_no,
        "price_paid": req.price,
        "passengers": req.passengers,
    }

    # INVOICE: Push Hotel Cost & UPDATE PHASE
    if booking:
        db.bookings.update_one(
            {"pnr": req.pnr, "user_id": x_user_id}, # 👈 Added Filter
            {
                "$set": {
                    "hotel_booking": hotel_data,
                    "status": "Completed",
                    "trip_phase": "CITY_EXPLORATION",
                },
                "$push": {
                    "expenses": {
                        "item_id": stay_booking_id,
                        "expense_type": "HOTEL",
                        "description": req.option_name,
                        "cost": req.price,
                        "status": "BOOKED",
                        "timestamp": datetime.now().isoformat(),
                    }
                },
                "$inc": {"total_amount": req.price},
            },
        )

        # FINAL INVOICE TRIGGER: Generate PDF and send via Telegram
        updated_booking = db.bookings.find_one({"pnr": req.pnr, "user_id": x_user_id}) # 👈 Added Filter
        if updated_booking and chat_id:
            try:
                pdf_path = generate_trip_invoice(updated_booking)
                send_invoice_via_telegram(
                    chat_id, pdf_path, updated_booking.get("total_amount", 0)
                )
                print(f"✅ Invoice successfully sent to {chat_id} for PNR {req.pnr}")
            except Exception as e:
                print(f"❌ Error sending invoice: {e}")

    guest_names = (
        ", ".join([p.get("name", "Guest") for p in req.passengers])
        if req.passengers
        else "Primary Guest"
    )
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

    confirmation_msg = (
        f"🏨 <b>STAY CONFIRMATION SUCCESSFUL</b>\n\n"
        f"Your city accommodation is locked & secured!\n\n"
        f"🏢 <b>Property:</b> {req.option_name}\n"
        f"🔢 <b>Room Allocated:</b> {room_no} (Guaranteed)\n"
        f"👥 <b>Guests Checked-in:</b> {guest_names}\n"
        f"🔖 <b>Booking Ref:</b> {stay_booking_id}\n"
        f"🔗 <b>Linked PNR:</b> {req.pnr}\n\n"
        f"<i>Show this message at the reception desk for instant check-in. Have a comfortable stay!</i>"
    )

    if chat_id:
        print(f"-> Sending hotel confirmation to Telegram Chat ID: {chat_id}")
        requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={"chat_id": chat_id, "text": confirmation_msg, "parse_mode": "HTML"},
        )

    return {
        "status": "success",
        "stay_booking_id": stay_booking_id,
        "room_no": room_no,
        "pnr": req.pnr,
    }

# ---------------------------------------------------------
# 📊 NEW ROUTE: FETCH INVOICE SUMMARY FOR REACT
# ---------------------------------------------------------
@app.get("/api/trips/{pnr}/invoice-summary")
async def get_invoice_summary(pnr: str, x_user_id: str = Header(None)): # 👈 Added Header
    try:
        if not x_user_id:
            return {"status": "error", "message": "Unauthorized"}
            
        trip = db.bookings.find_one({"pnr": pnr, "user_id": x_user_id}) # 👈 Added Filter
        if not trip:
            return {"status": "error", "message": "Trip not found"}

        # Simulating LLM Summary
        total = trip.get("total_amount", 0)
        items = [
            f"{exp['expense_type']} (₹{exp['cost']})"
            for exp in trip.get("expenses", [])
        ]
        summary_text = f"Your entire trip with Agentra is complete! You spent a total of ₹{total}. This includes: {', '.join(items)}."

        return {
            "status": "success",
            "total_amount": total,
            "expenses": trip.get("expenses", []),
            "summary": summary_text,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ---------------------------------------------------------
# 🗺️ NEW ROUTE: SMART ITINERARY GENERATOR
# ---------------------------------------------------------
import os
import json
import google.generativeai as genai
from pydantic import BaseModel

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


class ItineraryRequest(BaseModel):
    pnr: str
    purpose: str
    duration_days: int
    primary_location: str


# ---------------------------------------------------------
# 🗺️ SMART ITINERARY GENERATOR
# ---------------------------------------------------------


@app.post("/api/trips/{pnr}/generate-itinerary")
async def generate_smart_itinerary(pnr: str, req: ItineraryRequest, x_user_id: str = Header(None)): # 👈 Added Header
    try:
        if not x_user_id:
            return {"status": "error", "message": "Unauthorized"}

        # 1. FETCH DIRECTLY USING PROPER PNR AND USER ID
        booking = db.bookings.find_one({"pnr": pnr, "status": "Completed", "user_id": x_user_id}) # 👈 Added Filter
        if not booking:
            return {"status": "error", "message": f"Booking not found for PNR {pnr}"}

        destination = booking.get("journey", "").split(" to ")[-1].split(",")[0].strip()
        passengers = booking.get("seats", "")

        # 2. Strict Prompt for Gemini
        system_prompt = f"""
        You are a highly intelligent travel concierge for Agentra. 
        Create a detailed, realistic, and optimized travel itinerary for a user traveling to {destination}.
        
        CONTEXT:
        - Purpose of trip: {req.purpose}
        - Primary location/area of interest: {req.primary_location}
        - Duration: {req.duration_days} days
        - Passenger details: {passengers}
        
        🚨 CRITICAL RULES (MUST FOLLOW STRICTLY):
        1. 🌍 GEOGRAPHY: You MUST strictly generate the itinerary ONLY for {req.primary_location}. Do NOT hallucinate generic tourist cities.
        2. ⏳ EXACT DURATION: You MUST generate EXACTLY {req.duration_days} days in your JSON array. If duration is 3, the array MUST contain Day 1, Day 2, and Day 3. DO NOT output fewer or more days than requested.
        3. 🎯 STRICT PURPOSE ALIGNMENT: The purpose is '{req.purpose}'. 
           - If Business/Work: Focus strictly on business districts, quick corporate lunches, networking spots, and very light evening relaxation. Do NOT pack the day with historical sightseeing.
           - If Leisure/Tourism: Maximize sightseeing, local food, and cultural exploration.
        
        - NEVER output plain text. You MUST output ONLY valid JSON matching this exact structure:
        
        {{
            "itinerary": [
                {{
                    "day": "Day 1",
                    "theme": "Arrival & Business Focus",
                    "places": [
                        {{
                            "name": "Name of Place",
                            "image_search_query": "high quality image of [Place Name] [City]",
                            "address": "Full physical address",
                            "timing": "e.g., 10:00 AM - 5:00 PM",
                            "ticket_pricing": "e.g., Free or ₹500",
                            "rating": "e.g., 4.5",
                            "description": "2-3 sentences explaining.",
                            "map_query": "Place Name, City"
                        }}
                    ]
                }}
            ]
        }}
        """

        # 3. Call Gemini Model
        model = genai.GenerativeModel(
            "gemini-2.5-flash",
            generation_config={"response_mime_type": "application/json"},
        )

        response = model.generate_content(system_prompt)
        raw_text = response.text.strip()

        if raw_text.startswith("```"):
            raw_text = (
                raw_text.strip("`")
                .replace("json\n", "", 1)
                .replace("json", "", 1)
                .strip()
            )

        try:
            itinerary_json = json.loads(raw_text)
        except Exception as json_err:
            print(f"❌ JSON PARSE ERROR: {json_err}")
            print(f"RAW TEXT WAS: {raw_text}")
            return {"status": "error", "message": f"JSON Parse Failed: {json_err}"}

        # 4. SAVE ITINERARY DIRECTLY TO THIS SPECIFIC PNR AND USER
        update_result = db.bookings.update_one(
            {"pnr": pnr, "user_id": x_user_id}, {"$set": {"itinerary_data": itinerary_json}} # 👈 Added Filter
        )

        print(
            f"✅ DB Update matched: {update_result.matched_count}, modified: {update_result.modified_count}"
        )

        return {"status": "success", "data": itinerary_json}

    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/trips/{pnr}/itinerary")
async def get_saved_itinerary(pnr: str, x_user_id: str = Header(None)): 
    try:
        if not x_user_id:
             return {"status": "error", "message": "Unauthorized"}
             
        booking = db.bookings.find_one({"pnr": pnr, "user_id": x_user_id}) 

        if booking and "itinerary_data" in booking:
            return {"status": "success", "data": booking["itinerary_data"]}

        return {"status": "error", "message": "No itinerary found in DB for this PNR."}
    except Exception as e:
        return {"status": "error", "message": str(e)}