import time
from gmail_client import get_service, yesterday_window
from email_text import get_email
from ai_client import summarise

svc = get_service()
s, e = yesterday_window()
msgs = svc.users().messages().list(userId="me", q=f"after:{s} before:{e}", maxResults=3).execute().get("messages", [])
for m in msgs:
    em = get_email(svc, m["id"])
    try:
        res, model = summarise(em["subject"], em["sender"], em["date"], em["body"])
        print("\n" + em["subject"][:70], "|", model)
        for k, v in res.items():
            print("  ", k, ":", v)
    except Exception as ex:
        print("\nFAILED:", em["subject"][:70], "|", ex)
    time.sleep(4)
