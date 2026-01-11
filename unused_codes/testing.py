# import os
# import datetime
# import pytz
# from google.auth.transport.requests import Request
# from google.oauth2.credentials import Credentials
# from google_auth_oauthlib.flow import InstalledAppFlow
# from googleapiclient.discovery import build

# # Use the full 'calendar' scope to test both reading and the permissions needed for booking later
# SCOPES = ['https://www.googleapis.com/auth/calendar']

# def test_google_calendar_connection():
#     creds = None
#     # token.json stores the user's access and refresh tokens
#     if os.path.exists('token.json'):
#         creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
#     # If there are no (valid) credentials available, let the user log in.
#     if not creds or not creds.valid:
#         if creds and creds.expired and creds.refresh_token:
#             creds.refresh(Request())
#         else:
#             print("[*] No valid token found. Opening browser for authentication...")
#             if not os.path.exists(r'client_secret_945027684471-abdh1mmbidcvd00dvqmedj6cgc7k1sko.apps.googleusercontent.com.json'):
#                 print("[!] ERROR: 'credentials.json' not found! Download it from Google Cloud Console.")
#                 return
            
#             flow = InstalledAppFlow.from_client_secrets_file(r'client_secret_945027684471-abdh1mmbidcvd00dvqmedj6cgc7k1sko.apps.googleusercontent.com.json', SCOPES)
#             creds = flow.run_local_server(port=0)
            
#         # Save the credentials for the next run
#         with open('token.json', 'w') as token:
#             token.write(creds.to_json())
#             print("[+] Authentication successful. 'token.json' created.")

#     try:
#         service = build('calendar', 'v3', credentials=creds)

#         # Set Timezone to India (IST)
#         ist = pytz.timezone('Asia/Kolkata')
#         now_ist = datetime.datetime.now(ist)
        
#         # Look ahead 3 days from exactly right now
#         three_days_later = (now_ist + datetime.timedelta(days=3))

#         print(f"\n--- GOOGLE CALENDAR CONNECTION TEST ---")
#         print(f"Current Time (IST): {now_ist.strftime('%Y-%m-%d %I:%M %p')}")
#         print(f"Scanning up to:    {three_days_later.strftime('%Y-%m-%d %I:%M %p')}")
#         print("-" * 40)

#         # Call the Calendar API to list events
#         events_result = service.events().list(
#             calendarId='primary',
#             timeMin=now_ist.isoformat(),
#             timeMax=three_days_later.isoformat(),
#             singleEvents=True,
#             orderBy='startTime'
#         ).execute()
        
#         events = events_result.get('items', [])

#         if not events:
#             print('[-] No events found in the next 3 days.')
#             print("[TIP] Go to your calendar in a browser and add a test event to see it here!")
#         else:
#             print(f"[+] Successfully retrieved {len(events)} events:")
#             for event in events:
#                 start = event['start'].get('dateTime', event['start'].get('date'))
#                 # Convert back to IST for display
#                 start_dt = datetime.datetime.fromisoformat(start.replace('Z', '+00:00')).astimezone(ist)
#                 print(f" -> {start_dt.strftime('%d %b, %I:%M %p')}: {event.get('summary', '(No Title)')}")
        
#         print("-" * 40)
#         print("[SUCCESS] API plumbing is functional. You can proceed to Agent Integration.")

#     except Exception as e:
#         print(f"[!] API ERROR: {e}")

# if __name__ == '__main__':
#     test_google_calendar_connection()

import pandas as pd

df = pd.DataFrame(data = {})

