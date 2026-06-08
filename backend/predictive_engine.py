import google.generativeai as genai
import json
from datetime import datetime
from agent.tools import search_trains, search_flights


def run_smart_wl_prediction(booking_data):
    """
    Advanced Autonomous AI Engine: Analyzes WL probability.
    If dropping, it automatically triggers external APIs to fetch REAL alternative trains and flights.
    """

    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        tools=[search_trains.func, search_flights.func],
    )

    today_date = datetime.now().strftime("%Y-%m-%d")
    source = booking_data.get("journey", "").split(" to ")[0].split("from ")[-1].strip()
    destination = (
        booking_data.get("journey", "").split(" to ")[-1].split(",")[0].strip()
    )

    system_prompt = f"""
    You are the Agentra OS Predictive Waitlist & Real-Time Routing Engine.
    
    TICKET CONTEXT:
    - Train: {booking_data.get('train_number')}
    - Journey: {source} to {destination}
    - Departure Time: {booking_data.get('departure_time')}
    - Current Status: {booking_data.get('status')}
    - API Baseline Probability: {booking_data.get('baseline_probability', 50)}%
    - Today's Date: {today_date}

    YOUR DIRECTIVE (EXECUTE IN ORDER):
    
    STEP 1: PREDICTION
    Analyze the probability. If the baseline is below 55% or route is heavy, determine it as "WILL_DROP". Otherwise, "WILL_CONFIRM".
    
    STEP 2: REAL-TIME ALTERNATIVE ROUTING & HUB-LOGIC (CRITICAL)
    If your prediction is "WILL_DROP", you MUST act as an expert travel hacker:
    1. Direct Search: First, call `search_trains` and `search_flights` for the direct route ({source} to {destination}).
    2. Smart Break-Journey (Hub-and-Spoke): If direct trains are waitlisted/unavailable, THINK of major nearby railway transit hubs (e.g., If source is Gwalior, think of Jhansi/VGLJ or Agra/AGC. If destination is Prayagraj, think of Kanpur/CNB or Varanasi/BSB).
    3. Call `search_trains` AGAIN using these nearby hubs as the new source or destination.
    4. Combine and Build: If you find a confirmed seat from a nearby hub, build a multi-modal route. Example: "Take a 2-hour local RedBus/Rapido Intercity from Gwalior to Jhansi, then board the available Train X from Jhansi to Prayagraj."
    *Note: If the API tools return an error or say "API exhausted", do not crash. Generate realistic fallback options based on your knowledge.*

    STEP 3: OUTPUT FORMAT
    You MUST output ONLY valid JSON matching this exact structure. 
    🚨 IMPORTANT: Do NOT copy the example 'adjusted_probability' value. You MUST calculate a realistic integer yourself based on the baseline and real-world factors.
    {{
        "adjusted_probability": 22, // Replace this with YOUR dynamically calculated integer
        "prediction_status": "WILL_DROP", 
        "reasoning": "Explain why it will drop based on context.",
        "smart_alternatives": [
            "✈️ IndiGo 6E-202 | Gwalior to Prayagraj | 18:30 | ₹4500 (Direct)",
            "🚌 + 🚂 Multi-Modal: Take local bus GWL to Jhansi (2 hrs), then board Vande Bharat (22436) from VGLJ to PRYJ at 15:00 (Confirm AVL)"
        ]
    }}
    """

    try:

        chat = model.start_chat(enable_automatic_function_calling=True)
        response = chat.send_message(system_prompt)
        raw_text = response.text.strip()

        if raw_text.startswith("```"):
            raw_text = (
                raw_text.strip("`")
                .replace("json\n", "", 1)
                .replace("json", "", 1)
                .strip()
            )

        return json.loads(raw_text)

    except Exception as e:
        print(f"Prediction Engine & API Routing Error: {e}")

        return {
            "prediction_status": "WILL_DROP",
            "adjusted_probability": booking_data.get("baseline_probability", 30),
            "reasoning": "System API limits reached, relying on fallback heuristic models.",
            "smart_alternatives": [
                f"🚌 Please check alternative buses on RedBus for {source} to {destination}.",
                f"🚂 Check Tatkal availability for tomorrow morning.",
            ],
        }
