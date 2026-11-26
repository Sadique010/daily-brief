import datetime as dt
from zoneinfo import ZoneInfo
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
IST = ZoneInfo("Asia/Kolkata")


def get_service():
    creds = None
    try:
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    except Exception:
        pass
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as f:
            f.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def yesterday_window():
    today = dt.datetime.now(IST).replace(hour=0, minute=0, second=0, microsecond=0)
    start = today - dt.timedelta(days=1)
    return int(start.timestamp()), int(today.timestamp())


if __name__ == "__main__":
    svc = get_service()
    start, end = yesterday_window()
    res = svc.users().messages().list(userId="me", q=f"after:{start} before:{end}", maxResults=5).execute()
    msgs = res.get("messages", [])
    print(f"Found {len(msgs)} (max 5 shown)")
    for m in msgs:
        d = svc.users().messages().get(userId="me", id=m["id"], format="metadata",
                                       metadataHeaders=["Subject", "From", "Date"]).execute()
        h = {x["name"]: x["value"] for x in d["payload"]["headers"]}
        print("-", h.get("Subject"), "|", h.get("From"), "|", h.get("Date"))
