import argparse
import datetime as dt
import json
import os
import re
import time
from email.utils import parseaddr

from gmail_client import get_service, IST
from email_text import get_email
from ai_client import summarise
from publish import publish
from crypto import get_key, decrypt_obj

OUT = "private"


def window(day):
    start = dt.datetime.combine(day, dt.time(0, 0), tzinfo=IST)
    return int(start.timestamp()), int((start + dt.timedelta(days=1)).timestamp())


def list_ids(svc, s, e, limit):
    ids, tok = [], None
    q = f"after:{s} before:{e} -in:sent -in:drafts"
    while True:
        r = svc.users().messages().list(userId="me", q=q, pageToken=tok, maxResults=100).execute()
        ids += [m["id"] for m in r.get("messages", [])]
        tok = r.get("nextPageToken")
        if not tok or (limit and len(ids) >= limit):
            break
    return ids[:limit] if limit else ids


def save(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def write_index():
    days = []
    for fn in sorted(os.listdir(OUT), reverse=True):
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}\.json", fn):
            d = json.load(open(f"{OUT}/{fn}", encoding="utf-8"))
            days.append({"date": d["date"], "emails": len(d["emails"]), "failed": d.get("failed", 0)})
    save(f"{OUT}/index.json", {"days": days})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    now = dt.datetime.now(IST)
    day = dt.date.fromisoformat(a.date) if a.date else (now - dt.timedelta(days=1)).date()
    if day >= now.date():
        raise SystemExit("Date must be before today (IST).")

    os.makedirs(OUT, exist_ok=True)
    path = f"{OUT}/{day}.json"
    if os.path.exists(path):
        data = json.load(open(path, encoding="utf-8"))
    elif os.path.exists(f"docs/data/{day}.enc"):
        data = decrypt_obj(open(f"docs/data/{day}.enc").read(), get_key())
    else:
        data = {"date": str(day), "emails": [], "failed_items": []}
    done = {e["id"] for e in data["emails"]}

    svc = get_service()
    s, e = window(day)
    ids = list_ids(svc, s, e, a.limit)
    todo = [i for i in ids if i not in done]
    print(f"{day}: {len(ids)} found, {len(done)} already done, {len(todo)} to process")

    data["partial"] = bool(a.limit)
    data["failed"] = len(data["failed_items"])
    save(path, data)

    for n, mid in enumerate(todo, 1):
        subj = "?"
        try:
            em = get_email(svc, mid)
            subj = em["subject"]
            res, model = summarise(em["subject"], em["sender"], em["date"], em["body"])
            name, addr = parseaddr(em["sender"])
            rec = {"id": mid, "subject": em["subject"], "sender_name": name or addr,
                   "sender_email": addr,
                   "received": dt.datetime.fromtimestamp(em["internal"] / 1000, IST).isoformat(timespec="seconds"),
                   **res}
            data["emails"].append(rec)
            data["failed_items"] = [f for f in data["failed_items"] if f["id"] != mid]
            print(f"[{n}/{len(todo)}] ok     {subj[:60]}")
        except Exception as ex:
            data["failed_items"] = [f for f in data["failed_items"] if f["id"] != mid]
            data["failed_items"].append({"id": mid, "subject": subj, "error": str(ex)[:200]})
            print(f"[{n}/{len(todo)}] FAILED {subj[:60]} | {str(ex)[:100]}")
        data["failed"] = len(data["failed_items"])
        data["generated"] = dt.datetime.now(IST).isoformat(timespec="seconds")
        save(path, data)
        time.sleep(4)

    write_index()
    publish()
    print(f"Done: {len(data['emails'])} ok, {data['failed']} failed. Saved to {path}")


if __name__ == "__main__":
    main()
