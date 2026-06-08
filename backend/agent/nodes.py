import os
import datetime
from dotenv import load_dotenv
from pymongo import MongoClient
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage
from langgraph.prebuilt import ToolNode
from agent.state import AgentState
from agent.tools import travel_tools

load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")
groq_api_key = os.getenv("GROQ_API_KEY")


llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash", google_api_key=gemini_api_key, temperature=0
)


llm_with_tools = llm.bind_tools(travel_tools)
tool_node = ToolNode(travel_tools)


try:
    MONGO_URL = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    sync_db = MongoClient(MONGO_URL).nexustravel
except Exception as e:
    print(f"DEBUG: Database connection failed: {e}")
    sync_db = None


def chatbot_node(state: AgentState):
    import datetime

    messages = state["messages"]

    current_datetime = datetime.datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")

    history_str = "No past bookings found."
    if sync_db is not None:
        try:
            recent_bookings = list(
                sync_db.bookings.find({}, {"_id": 0}).sort("timestamp", -1).limit(5)
            )
            if recent_bookings:
                history_str = "\n".join(
                    [
                        f"- PNR {b['pnr']}: {b['journey']} (Booked on: {b.get('timestamp', '')[:10]})"
                        for b in recent_bookings
                    ]
                )
        except Exception:
            history_str = "Database offline."

    dynamic_system_prompt = f"""You are Agentra, an elite transit orchestrator. 
    CURRENT SYSTEM DATE AND TIME: {current_datetime}.
    
    🧠 USER'S BOOKING HISTORY:
    {history_str}
    
    🚨 CRITICAL RULES FOR EXECUTION (MUST FOLLOW):
        1. NEVER AUTO-LOCK: You must NEVER automatically select, lock, or book a train/hotel for the user. 
        2. ONE TOOL AT A TIME: When a user asks to search for trains, ONLY call the `search_trains` tool and IMMEDIATELY STOP thinking. 
        3. YIELD TO UI: After calling `search_trains` or `Google Hotels`, just tell the user: "I have fetched the options. Please check the Workspace UI and click 'Details' to select one." DO NOT call `predict_delay` or any other tool until the user explicitly makes a choice.
        
        🚨 CRITICAL RULES FOR MULTI-TOOL CALLING (MUST FOLLOW):
        1. NEVER ASSUME USER CONSENT: Do NOT combine tools if authorization is required.
        2. THE "INTEL" RULE: If a user locks a train/flight, you MUST ONLY call the delay/pricing tool. DO NOT call `get_destination_intel` (Weather/Intel) until you have explicitly asked the user: "Would you like local intel?" and they reply with a "Yes".
        3. HALT EXECUTION: After providing the delay/pricing data, you MUST HALT and wait for the user's response.
    
    STRICT OPERATIONAL RULES:
    1. INTENT ROUTING: Flight queries -> `search_flights`. Train queries -> `search_trains`. Post-arrival stay/hotel queries -> `find_accommodations`.
    
    
    2. SMART CONCIERGE PROTOCOL:
       - PHASE 1/2: Output options and ask priority.
       
       - PHASE 3 (SMART ANALYSIS):
         IF IT IS A TRAIN: Output strictly:
         ✅ Train [Number] Locked!
         💰 Price: Standard IRCTC Fare (₹[User Price]).
         ⏳ Delay Risk: [Risk Level] (Avg Delay: [Formatted Delay]). [Reason].
         
         IF IT IS A FLIGHT: Output strictly:
         ✅ Flight [Airline Name & Number] Locked!
         💰 Price Analysis: [Steal Deal / Standard / Premium].
         💡 Recommendation: [Explicit advice to book or wait].
         ⏳ Delay Risk: Low Delay Risk (Historical on-time performance > 92%).
         
         FINALLY: Ask "Want me to fetch the weather and local intel for [Destination] before finalizing?"
         
       - PHASE 4 (WEATHER INTEL): 
         Output strictly (NO conversational text before this):
         📍 Destination Intel: [City]
         🌡️ Live Weather: [Detailed Weather]
         🎯 Season Verdict: [Go/No-Go]. [Detailed advice].
         🚕 Pro-Tip: [Local transit tip].
         🍛 Must Try: [Food recommendation].
         Shall I initiate your booking now?
         
       - PHASE 5: Ask "Are you traveling alone, or with co-passengers? Please provide names and ages." STOP AND WAIT.
       
       - PHASE 6: EXECUTE `create_draft_booking`. Output exactly:
         📋 Passenger Manifest Ready
         [List passengers]
         ⚠️ A secure Review window has opened. Please verify your details and pay there.
         [HIDDEN_DRAFT_ID: draft_id_from_tool]
         
       - PHASE 7: Triggered by "SYSTEM_PAYMENT_SUCCESS_TRIGGER...". Output exact payment success and boarding details ticket.

       - PHASE 8 (POST-ARRIVAL GREETING): When the user states they have reached their destination, output strictly:
         Welcome to [City]! 🎉 I hope your journey was comfortable. Where are you heading now in the city, what is the purpose of your trip, and for how many days are you staying? (DO NOT ask for distance).
         
       - PHASE 9 (ACCOMMODATION TOOL EXECUTION): Once the user provides their address, purpose, and stay days:
         1. YOU must internally estimate the distance from the station to their address in KM.
         2. Execute `find_accommodations` tool. 
         3. Output exactly: 
         🔍 Analyzing optimal transit vs city stay logistics... I have rendered the best options in your Workspace!
         
       - PHASE 10 (STAY CONFIRMATION): Triggered by "SYSTEM_STAY_BOOKED...". Output exactly:
         🏨 Accommodation Secured!
         [Repeat the details provided in the trigger]. Your live tracking and emergency guard systems are active for the stay.
         
    3. NEVER use asterisks (like ** or *) in your text.
    
    """

    valid_history = [m for m in messages if m.type != "system"]
    valid_history.insert(0, SystemMessage(content=dynamic_system_prompt))

    last_msg = messages[-1] if messages else None

    if last_msg and last_msg.type == "human":
        msg_text = last_msg.content.lower().strip()

        ai_msg = (
            messages[-2] if len(messages) >= 2 and messages[-2].type == "ai" else None
        )
        ai_text = ai_msg.content.lower() if ai_msg else ""

        try:
            # SCENARIO 1: Weather Check
            is_weather_intent = "weather" in msg_text or "intel" in msg_text
            is_weather_yes = msg_text in ["yes", "yeah", "yep", "sure", "please"] and (
                "weather" in ai_text or "intel" in ai_text
            )

            if is_weather_intent or is_weather_yes:
                forced_llm = llm.bind_tools(
                    travel_tools, tool_choice="get_destination_intel"
                )
                return {
                    "messages": [forced_llm.invoke(valid_history)],
                    "results_ready": True,
                }

            # SCENARIO 2: Train Locked (Analysis Phase)
            if "i have locked the train" in msg_text:
                forced_llm = llm.bind_tools(
                    travel_tools, tool_choice="predict_train_delay"
                )
                return {
                    "messages": [forced_llm.invoke(valid_history)],
                    "results_ready": True,
                }

            # SCENARIO 3: Draft Booking (Passenger Info)
            if "names and ages" in ai_text and len(msg_text) > 3:
                forced_llm = llm.bind_tools(
                    travel_tools, tool_choice="create_draft_booking"
                )
                return {
                    "messages": [forced_llm.invoke(valid_history)],
                    "results_ready": True,
                }

        except Exception as e:
            print(
                f"DEBUG: Forced tool call failed gracefully. Falling back to normal flow. Error: {e}"
            )
            pass  # Failsafe: Falls back to standard chat instead of crashing

    response = llm_with_tools.invoke(valid_history)

    return {"messages": [response], "results_ready": True}
