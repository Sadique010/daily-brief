import os
from google import genai

key = None
for line in open(".env"):
    if line.startswith("GEMINI_API_KEY="):
        key = line.split("=", 1)[1].strip()

client = genai.Client(api_key=key)
r = client.models.generate_content(
    model="gemini-3.5-flash-lite",
    contents="Reply with exactly: Gemini connected",
)
print(r.text)
