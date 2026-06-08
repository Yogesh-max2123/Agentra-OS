from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict, List, Optional, Any


class MessageDict(BaseModel):
    sender: str
    text: str


class ChatRequest(BaseModel):
    message: str
    history: List[MessageDict] = []
    session_id: Optional[str] = "guest_123"


class LogEntry(BaseModel):
    time: str
    text: str
    type: str


class ChatResponse(BaseModel):
    agent_message: str
    logs: List[LogEntry]
    results_ready: bool
    action_data: Optional[Any] = None
    smart_chips: Optional[List[str]] = []


class ExpenseItem(BaseModel):
    item_id: str
    expense_type: str = Field(..., description="TRAIN_TICKET, CAB, FOOD, HOTEL")
    description: str
    cost: float
    status: str = "BOOKED"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class BookingSchema(BaseModel):
    pnr: str
    chat_id: str
    journey: str
    departure_time: datetime
    arrival_time: datetime
    passenger_name: str
    gender: str = Field(..., description="Male, Female, or Other")
    is_solo: bool = False

    passengers: List[Dict[str, Any]] = []

    seats: str

    expenses: List[ExpenseItem] = []
    total_amount: float = 0.0

    status: str = "Confirmed & Paid"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class StayRequest(BaseModel):
    pnr: str
    purpose: str
    destination_address: str
    duration_hours: int
    distance_from_station_km: float
