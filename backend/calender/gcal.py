
import base64
import json
import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv
from dateutil.parser import parse
from datetime import timedelta


load_dotenv()
import os

SCOPES = ['https://www.googleapis.com/auth/calendar']
encoded = os.getenv("GOOGLE_CREDENTIALS_JSON")
CALENDAR_ID = os.getenv("CALENDAR_ID")

print("base64 json is ",encoded)

def build_service():
    if not encoded:
        raise ValueError("❌ GOOGLE_CREDENTIALS_BASE64 not set")

    try:
        decoded = base64.b64decode(encoded)
        creds_dict = json.loads(decoded)
    except Exception as e:
        raise ValueError(f"❌ Failed to decode credentials: {e}")

    credentials = service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return build('calendar', 'v3', credentials=credentials)

# 🔧 This is your shared object
service = build_service()

# 🕓 Function 1: Check availability
def check_availability(date_str: str):
    """
    Takes an ISO date string (e.g., '2025-07-06') and returns busy time slots on that day.
    """
    date = datetime.datetime.fromisoformat(date_str)
    start_of_day = date.replace(hour=0, minute=0, second=0).isoformat() + 'Z'
    end_of_day = date.replace(hour=23, minute=59, second=59).isoformat() + 'Z'

    events_result = service.events().list(
        calendarId=CALENDAR_ID,
        timeMin=start_of_day,
        timeMax=end_of_day,
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    busy_slots = []
    for event in events_result.get('items', []):
        start = event['start'].get('dateTime')
        end = event['end'].get('dateTime')
        if start and end:
            busy_slots.append(f"{start} → {end}")

    return busy_slots

# 📅 Function 2: Book Event
def book_event(title: str, start_datetime: str, end_datetime: str):
    """
    Books an event in Google Calendar.
    datetime format: 'YYYY-MM-DDTHH:MM:SS' (ISO 8601)
    """
    event = {
        'summary': title,
        'start': {
            'dateTime': start_datetime,
            'timeZone': 'Asia/Kolkata'
        },
        'end': {
            'dateTime': end_datetime,
            'timeZone': 'Asia/Kolkata'
        }
    }

    try:
        created_event = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        return f"✅ Event booked successfully: {created_event.get('htmlLink')}"
    except Exception as e:
        return f"❌ Failed to book event: {str(e)}"

def get_free_slots(date_str: str, duration_minutes: int = 30):
    """
    Returns free time slots of at least `duration_minutes` on the given date.
    """

    busy_times_raw = check_availability(date_str)

    # Parse busy times into datetime ranges
    busy_ranges = []
    for slot in busy_times_raw:
        try:
            start_str, end_str = slot.split(" → ")
            start = parse(start_str)
            end = parse(end_str)
            busy_ranges.append((start, end))
        except:
            continue

    # Sort just in case
    busy_ranges.sort()

    # Set work day limits (e.g., 9 AM to 6 PM)
    date = datetime.datetime.fromisoformat(date_str)
    work_start = date.replace(hour=9, minute=0, second=0)
    work_end = date.replace(hour=18, minute=0, second=0)

    # Find gaps between busy slots
    free_slots = []
    current_time = work_start

    for start, end in busy_ranges:
        if current_time + timedelta(minutes=duration_minutes) <= start:
            free_slots.append((current_time, start))
        current_time = max(current_time, end)

    # Final check: free slot between last meeting and end of work day
    if current_time + timedelta(minutes=duration_minutes) <= work_end:
        free_slots.append((current_time, work_end))

    # Format output
    formatted = [
        f"{slot[0].strftime('%H:%M')} → {slot[1].strftime('%H:%M')}"
        for slot in free_slots
    ]

    return formatted
