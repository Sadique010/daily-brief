import json, os, re
from crypto import DATA, get_key, encrypt_obj, decrypt_obj

PAT = re.compile(r"(\d{4}-\d{2}-\d{2})\.(json|enc)$")


def _info(d):
    return {"date": d["date"], "emails": len(d["emails"]), "failed": d.get("failed", 0)}


def publish():
    key = get_key()
    os.makedirs(DATA, exist_ok=True)
    days = {}
    if os.path.isdir("private"):
        for fn in os.listdir("private"):
            m = PAT.match(fn)
            if m and m.group(2) == "json":
                src = f"private/{fn}"
                out = f"{DATA}/{m.group(1)}.enc"
                d = json.load(open(src, encoding="utf-8"))
                if not os.path.exists(out) or os.path.getmtime(src) > os.path.getmtime(out):
                    open(out, "w").write(encrypt_obj(d, key))
                days[m.group(1)] = _info(d)
    for fn in os.listdir(DATA):
        m = PAT.match(fn)
        if m and m.group(2) == "enc" and m.group(1) not in days:
            days[m.group(1)] = _info(decrypt_obj(open(f"{DATA}/{fn}").read(), key))
    idx = {"days": [days[k] for k in sorted(days, reverse=True)]}
    open(f"{DATA}/index.enc", "w").write(encrypt_obj(idx, key))
    print(f"Published {len(days)} day(s) to {DATA}")
