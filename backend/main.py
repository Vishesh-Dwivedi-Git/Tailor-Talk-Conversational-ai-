from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain.agents import initialize_agent, AgentType
from langchain.chat_models import ChatOpenAI
from langchain.tools import tool
import dateparser
from datetime import datetime
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Import your calendar functions
from backend.calender.gcal import check_availability, book_event, get_free_slots

# Setup FastAPI
app = FastAPI()

# CORS to allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request model
class ChatRequest(BaseModel):
    message: str


def safe_parse_date(raw: str) -> str:
    """Parses human input like '6 July' and returns 'YYYY-MM-DD' using current year if needed."""
    # Append current year if user didn’t give one
    current_year = datetime.now().year
    if not any(char.isdigit() and len(char) == 4 for char in raw):  # no full year in input
        raw += f" {current_year}"

    dt = dateparser.parse(raw)
    if not dt:
        raise ValueError(f"Invalid date format: '{raw}'")

    return dt.strftime("%Y-%m-%d")  # ✅ returns ISO string

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
    print(f"📅 Tool: book_meeting called with title='{title}', start='{start}', end='{end}'")
    result = book_event(title, start, end)
    return result if result else "❌ Failed to book the event."


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
