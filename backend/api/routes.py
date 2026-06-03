from fastapi import APIRouter
from models.schemas import ChatRequest, ChatResponse
from agent.graph import nexus_graph
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
import datetime
import json

router = APIRouter()

# 1. HELPER FUNCTION: Price History ke last 7 entries ka data analyze karne ke liye
def get_price_summary(history_list):
    if not history_list or not isinstance(history_list, list): 
        return ""
    try:
        # Sirf last 7 entries (days) ka slice nikalte hain taaki tokens bachein
        recent = history_list[-7:]
        prices = [item['value'] for item in recent if isinstance(item, dict) and 'value' in item]
        
        if not prices:
            return ""
            
        avg = sum(prices) / len(prices)
        return f"Avg: ₹{avg:.0f}, Min: ₹{min(prices)}, Max: ₹{max(prices)}"
    except Exception as e:
        print(f"Error in generating price summary: {e}")
        return ""

@router.post("/chat", response_model=ChatResponse)
async def process_chat(request: ChatRequest):
    current_time = datetime.datetime.now().strftime("%I:%M:%S %p")
    logs = [
        {"time": current_time, "text": f"Received query: '{request.message}'", "type": "info"},
        {"time": current_time, "text": "Routing query with context history through LangGraph...", "type": "waiting"}
    ]
    
    try:
        # 2. Chat History Context build karna
        langchain_messages = []
        for msg in request.history:
            if msg.sender == "user":
                langchain_messages.append(HumanMessage(content=msg.text))
            elif msg.sender == "agent":
                langchain_messages.append(AIMessage(content=msg.text))
                
        # Current input text append karna
        langchain_messages.append(HumanMessage(content=request.message))

        initial_state = {
            "messages": langchain_messages,
            "session_id": request.session_id,
            "results_ready": False
        }
        
        # Graph execution
        final_state = nexus_graph.invoke(initial_state)
        
        # 3. TOOL DATA EXTRACTION & PRICE CONTEXT WINDOW LOGIC
        extracted_ui_data = None
        price_summary = ""
        
        for msg in reversed(final_state["messages"]):
            if isinstance(msg, ToolMessage):
                try:
                    parsed_tool_data = json.loads(msg.content)
                    if parsed_tool_data.get("status") == "success":
                        extracted_ui_data = parsed_tool_data
                        print(f"\n👉 [ROUTES DEBUG] UI Data Extracted successfully!\n")
                        
                        # API ke raw response se history array nikalna safely
                        # Agar flights data ke andar ya directly dictionary me priceHistory ho
                        history = parsed_tool_data.get("priceHistory", {}).get("history", [])
                        if not history and "data" in parsed_tool_data:
                            if isinstance(parsed_tool_data["data"], dict):
                                history = parsed_tool_data["data"].get("priceHistory", {}).get("history", [])
                        
                        if history:
                            price_summary = get_price_summary(history)
                        break
                except Exception as parse_err:
                    print(f"\n👉 [ROUTES DEBUG] Failed to parse tool data: {parse_err}\n")
                    pass

        # 4. Extract Final Reply from LLM (FIXED KACHRA PARSER)
        last_content = final_state["messages"][-1].content
        ai_reply = ""
        
        # Agar response list format me aaya (jo tumhare screenshot me hai)
        if isinstance(last_content, list):
            for block in last_content:
                if isinstance(block, dict) and "text" in block:
                    ai_reply += block["text"] + "\n"
                elif isinstance(block, str):
                    ai_reply += block + "\n"
        else:
            # Agar direct string aaya
            ai_reply = str(last_content)
            
        ai_reply = ai_reply.strip()
            
        if not ai_reply:
            ai_reply = "I have fetched the real-time transit status for you."

        # 5. FIXED: Agar user booking/lock kar raha hai, toh summary append karo safely
        if price_summary and ("locked" in request.message.lower() or "price" in request.message.lower()):
            ai_reply += f"\n\n[Stats: {price_summary}]"
        # 6. SMART CHIPS GENERATION (Dynamic for Trains & Flights)
        chips = []
        if extracted_ui_data:
            if extracted_ui_data.get("type") == "trains":
                chips = ["⚡ Fastest Options", "💰 Budget Friendly", "💺 Best Comfort"]
            elif extracted_ui_data.get("type") == "flights":
                chips = ["⚡ Non-stop Flights", "💰 Cheapest Fares", "📅 Check Weather"]
            
        logs.append({"time": datetime.datetime.now().strftime("%I:%M:%S %p"), "text": "Gemini tool orchestration complete.", "type": "success"})
        
        return ChatResponse(
            agent_message=ai_reply.strip(),
            logs=logs,
            results_ready=True, 
            action_data=extracted_ui_data,
            smart_chips=chips
        )
            
    except Exception as e:
        # Emergency Error Handling block to prevent frontend crash
        logs.append({"time": datetime.datetime.now().strftime("%I:%M:%S %p"), "text": f"Execution Error: {str(e)}", "type": "error"})
        return ChatResponse(
            agent_message="System Error: Encountered an issue inside the LangGraph engine workflow.",
            logs=logs,
            results_ready=False,
            action_data=None,
            smart_chips=[]
        )