from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain.agents import initialize_agent, AgentType
from langchain_openai import ChatOpenAI
from langchain.tools import tool
import dateparser
from datetime import datetime
from dotenv import load_dotenv
import os
from dateutil.parser import parse

# Load environment variables
load_dotenv()

# Import your calendar functions
from calender.gcal import check_availability, book_event, get_free_slots

# Setup FastAPI
app = FastAPI()

# CORS to allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://calender0talk.streamlit.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request model
class ChatRequest(BaseModel):
    message: str

from datetime import datetime, timedelta
import dateparser

def safe_parse_date(raw: str) -> str:
    """
    Parses human-readable date strings (e.g., 'tomorrow', '6 July') into ISO format.
    Handles keywords like 'tomorrow', 'lunch', 'dinner', and appends year 2025 if not provided.
    Returns: ISO 8601 datetime string (YYYY-MM-DDTHH:MM:SS)
    """
    raw = raw.lower().strip()

    # Handle time-related keywords
    time_keywords = {
        "morning": "9 AM",
        "afternoon": "2 PM",
        "evening": "6 PM",
        "lunch": "1 PM",
        "dinner": "8 PM",
        "tonight": "9 PM",
    }

    for keyword, replacement in time_keywords.items():
        if keyword in raw:
            raw = raw.replace(keyword, replacement)

    # Handle "tomorrow", "today", "yesterday" manually for context
    today = datetime.now()

    if "tomorrow" in raw:
        date = today + timedelta(days=1)
        raw = raw.replace("tomorrow", date.strftime("%d %B"))
    elif "today" in raw:
        raw = raw.replace("today", today.strftime("%d %B"))
    elif "yesterday" in raw:
        date = today - timedelta(days=1)
        raw = raw.replace("yesterday", date.strftime("%d %B"))

    # Append 2025 if no 4-digit year is found
    if not any(len(token) == 4 and token.isdigit() for token in raw.split()):
        raw += " 2025"

    dt = dateparser.parse(raw, settings={"PREFER_DATES_FROM": "future"})

    if not dt:
        raise ValueError(f"❌ Could not parse date string: '{raw}'")

    return dt.strftime("%Y-%m-%dT%H:%M:%S")


# Tool: Check calendar
@tool(description="Check availability, returns busy slots for a given date.")
def check_calendar(date: str) -> str:
    """Check busy slots on a given date."""
    try:
        iso_date = safe_parse_date(date)
    except Exception as e:
        return f"⚠️ Could not understand date '{date}': {e}"

    busy_slots = check_availability(iso_date)
    return "✅ You're free all day." if not busy_slots else f"⏰ You're busy during: {busy_slots}"

# Tool: Book meeting
@tool(description="Book a meeting using title, start, and end time.")
def book_meeting(title: str, start: str, end: str) -> str:
    """
    Books a calendar event with ISO 8601-compliant timestamps.
    Accepts human-readable times (e.g., '8 July 2024 9 PM')
    """
    try:
        # Parse and convert to ISO 8601 with timezone
        start_dt = parse(start)
        end_dt = parse(end)

        start_iso = start_dt.isoformat()
        end_iso = end_dt.isoformat()

        print(f"📅 Booking: {title} | {start_iso} → {end_iso}")
        return book_event(title, start_iso, end_iso)

    except Exception as e:
        return f"❌ Failed to parse time or book event: {str(e)}"


# Tool: Suggest free slots
@tool(description="Suggests free time slots for the given date and duration (in minutes).")
def suggest_free_slots(date: str, duration: int = 30) -> str:
    print(f"📅 Tool: suggest_free_slots called with date={date}, duration={duration}")
    slots = get_free_slots(date, duration)
    if not slots:
        return "❌ No free slots available for that duration."
    return f"✅ You're free at: {', '.join(slots)}"

# LLM: HuggingFace Mistral
llm = ChatOpenAI(
    model="mistral-medium",  # or "mistral-small"
    temperature=0.5,
    openai_api_key=os.getenv("MISTRAL_API_KEY"),
    openai_api_base="https://api.mistral.ai/v1",  # ✅ Important
)
agent = initialize_agent(
    tools=[check_calendar, book_meeting, suggest_free_slots],
    llm=llm,
    agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

# Chat endpoint
# Chat endpoint with full logging
@app.post("/chat")
async def chat(request: ChatRequest):
    print("\n🔹🔹 Incoming request to /chat 🔹🔹")
    print("📨 User message:", request.message)

    try:
        response = agent.run(request.message)
        print("✅ Agent response:", response)
        return {"response": response}

    except Exception as e:
        print("❌ Agent crashed!")
        import traceback
        traceback.print_exc()  # full error dump
        return {"response": f"⚠️ Agent Error: {str(e)}"}
