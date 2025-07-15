from mcp.server.fastmcp import FastMCP
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
import json
import datetime
import parsedatetime
from dotenv import load_dotenv
from typing import Optional, List

# Load environment variables
load_dotenv()

# Create an MCP server
mcp = FastMCP("mcp-calendar")

# If modifying these scopes, delete the token file.
SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service():
    """Initialize and return Google Calendar service."""
    creds = None
    token_file = os.getenv('GOOGLE_TOKEN_FILE', 'token.json')

    # Load existing token
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    # If no valid credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_config({
                "installed": {
                    "client_id": os.getenv('GOOGLE_CLIENT_ID'),
                    "client_secret": os.getenv('GOOGLE_CLIENT_SECRET'),
                    "redirect_uris": [os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost')],
                    "auth_uri": os.getenv('GOOGLE_AUTH_URI', 'https://accounts.google.com/o/oauth2/auth'),
                    "token_uri": os.getenv('GOOGLE_TOKEN_URI', 'https://oauth2.googleapis.com/token')
                }
            }, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open(token_file, 'w') as token:
            token.write(creds.to_json())

    return build('calendar', 'v3', credentials=creds)

def parse_natural_datetime(text: str) -> datetime.datetime:
    """Convert natural language time to datetime object."""
    cal = parsedatetime.Calendar()
    time_struct, parse_status = cal.parse(text)
    return datetime.datetime(*time_struct[:6])

@mcp.tool()
def create_calendar_event(
    summary: str,
    start_time: str,
    end_time: Optional[str] = None,
    description: Optional[str] = None,
    location: Optional[str] = None,
    attendees: Optional[List[str]] = None
) -> str:
    """
    Create a Google Calendar event using natural language time inputs.
    
    Args:
        summary: Event title
        start_time: Natural language start time (e.g., "tomorrow at 2pm")
        end_time: Natural language end time (optional, defaults to 1 hour after start)
        description: Event description (optional)
        location: Event location (optional)
        attendees: List of attendee email addresses (optional)
    
    Returns:
        str: Success message with event details
    """
    try:
        service = get_calendar_service()
        
        # Parse start time
        start_datetime = parse_natural_datetime(start_time)
        
        # If no end time specified, set to 1 hour after start
        if not end_time:
            end_datetime = start_datetime + datetime.timedelta(hours=1)
        else:
            end_datetime = parse_natural_datetime(end_time)
        
        timezone = os.getenv('CALENDAR_TIMEZONE', 'UTC')
        event = {
            'summary': summary,
            'start': {
                'dateTime': start_datetime.isoformat(),
                'timeZone': timezone,
            },
            'end': {
                'dateTime': end_datetime.isoformat(),
                'timeZone': timezone,
            }
        }
        
        if description:
            event['description'] = description
        if location:
            event['location'] = location
        if attendees:
            event['attendees'] = [{'email': email} for email in attendees]
        
        event = service.events().insert(calendarId='primary', body=event).execute()
        
        return f"Event created successfully! Event ID: {event.get('id')}"
        
    except HttpError as error:
        return f"An error occurred: {error}"
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"
