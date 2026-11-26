import base64
from html.parser import HTMLParser


class _Strip(HTMLParser):
    def __init__(self):
        super().__init__()
        self.out, self.skip = [], 0

    def handle_starttag(self, t, a):
        if t in ("script", "style"):
            self.skip += 1

    def handle_endtag(self, t):
        if t in ("script", "style") and self.skip:
            self.skip -= 1

    def handle_data(self, d):
        if not self.skip:
            self.out.append(d)


def _decode(data):
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", "replace")


def _walk(part, plain, html):
    mt = part.get("mimeType", "")
    data = part.get("body", {}).get("data")
    if data and mt == "text/plain":
        plain.append(_decode(data))
    elif data and mt == "text/html":
        html.append(_decode(data))
    for p in part.get("parts", []) or []:
        _walk(p, plain, html)


def get_email(svc, msg_id, limit=4000):
    m = svc.users().messages().get(userId="me", id=msg_id, format="full").execute()
    h = {x["name"].lower(): x["value"] for x in m["payload"]["headers"]}
    plain, html = [], []
    _walk(m["payload"], plain, html)
    if plain:
        text = "\n".join(plain)
    else:
        s = _Strip()
        s.feed("\n".join(html))
        text = " ".join(s.out)
    text = " ".join(text.split())
    return {"id": m["id"], "subject": h.get("subject", ""), "sender": h.get("from", ""),
            "date": h.get("date", ""), "internal": int(m["internalDate"]), "body": text[:limit]}
