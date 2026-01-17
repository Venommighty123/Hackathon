import os
import pytz
from datetime import datetime, timedelta
from langchain_core.tools import tool
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

class CalendarService:
    def __init__(self):
        self.SCOPES = ['https://www.googleapis.com/auth/calendar']
        self.creds = self._authenticate()
        self.service = build('calendar', 'v3', credentials=self.creds)

    def _authenticate(self):
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', self.SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(r'credentials.json', self.SCOPES)
                creds = flow.run_local_server(port=0)
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        return creds
    
    def get_available_slots(self, date_str: str):
        try:
            ist = pytz.timezone('Asia/Kolkata')
            now_ist = datetime.now(ist)
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            is_today = target_date == now_ist.date()

            all_slots = ["09:00 AM", "10:00 AM", "11:00 AM", "12:00 PM", 
                         "01:00 PM", "02:00 PM", "03:00 PM", "04:00 PM"]

            start_dt = ist.localize(datetime.combine(target_date, datetime.min.time().replace(hour=9)))
            end_dt = ist.localize(datetime.combine(target_date, datetime.min.time().replace(hour=17)))
        
            body = {
                "timeMin": start_dt.isoformat(),
                "timeMax": end_dt.isoformat(),
                "items": [{"id": "primary"}]
            }
            events_result = self.service.freebusy().query(body=body).execute()
            busy_slots = events_result['calendars']['primary']['busy']

            available = []
            for slot in all_slots:
                slot_time = datetime.strptime(f"{date_str} {slot}", "%Y-%m-%d %I:%M %p")
                slot_dt = ist.localize(slot_time)

                if is_today and slot_dt < (now_ist + timedelta(minutes=30)):
                    continue

                is_busy = False
                for busy in busy_slots:
                    b_start = datetime.fromisoformat(busy['start'].replace('Z', '+00:00')).astimezone(ist)
                    b_end = datetime.fromisoformat(busy['end'].replace('Z', '+00:00')).astimezone(ist)
                    if b_start <= slot_dt < b_end:
                        is_busy = True
                        break
            
                if not is_busy:
                    available.append(slot)

            return available if available else ["No slots available for this date."]

        except Exception as error:
            print(f"[!] Error in get_available_slots: {error}")
            return []

    def book_meeting(self, emp_id: str, start_time_str: str, agenda: str):
        """
        Creates an event on the calendar in IST.
        Expected start_time_str from LLM: 'YYYY-MM-DDTHH:MM:SS' 
        (The LLM should ideally provide the time in 24h format)
        """
        try:
            ist = pytz.timezone('Asia/Kolkata')

            clean_time = start_time_str.split('+')[0].replace('Z', '')
            naive_dt = datetime.fromisoformat(clean_time)

            start_dt = ist.localize(naive_dt)
            end_dt = start_dt + timedelta(minutes=30)

            event = {
                'summary': f'HR Meeting: {emp_id}',
                'description': agenda,
                'start': {
                    'dateTime': start_dt.isoformat(),
                    'timeZone': 'Asia/Kolkata',
                },
                'end': {
                    'dateTime': end_dt.isoformat(),
                    'timeZone': 'Asia/Kolkata',
                },
                'reminders': {
                    'useDefault': True,
                },
            }

            event_result = self.service.events().insert(calendarId='primary', body=event).execute()
        
            link = event_result.get('htmlLink')
            print(f"[+] Meeting Booked in IST: {link}")
            return {"status": "success", "link": link}

        except Exception as error:
            print(f"[!] Error booking meeting: {error}")
            return {"status": "error", "message": str(error)}

calendar_api = CalendarService()

@tool
def fetch_slots(date: str):
    """Queries available 30-minute slots. Returns current time context and slots."""
    ist = pytz.timezone('Asia/Kolkata')
    current_time = datetime.now(ist).strftime("%I:%M %p")
    slots = calendar_api.get_available_slots(date)
    
    return {
        "requested_date": date,
        "current_time_right_now": current_time,
        "available_slots": slots
    }

@tool
def schedule_meeting(emp_id: str, date: str, time_slot: str, topic: str):
    """
    Books the meeting. 
    'date' must be YYYY-MM-DD. 
    'time_slot' must be 'HH:MM AM/PM' (e.g. '09:00 AM').
    """
    try:
        time_obj = datetime.strptime(time_slot.strip(), "%I:%M %p")
        time_24h = time_obj.strftime("%H:%M:%S")
        combined_iso = f"{date}T{time_24h}"
        
        return calendar_api.book_meeting(emp_id, combined_iso, topic)
    except Exception as e:
        return f"Booking Failed: Ensure time_slot is format 'HH:MM AM/PM'. Error: {e}"

calendar_tools = [fetch_slots, schedule_meeting]