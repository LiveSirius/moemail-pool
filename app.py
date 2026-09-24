import os
import time
import re
import asyncio
import json
from aiohttp import web, ClientSession

API_BASE = os.getenv("MOEMAIL_BASE", "").rstrip("/")
API_KEY = os.getenv("MOEMAIL_KEY", "")
DOMAIN = os.getenv("MOEMAIL_DOMAIN", "")

DATA_DIR = os.getenv("DATA_DIR", "/data")
POOL_FILE = os.path.join(DATA_DIR, "pool.json")
os.makedirs(DATA_DIR, exist_ok=True)

def load_pool():
    if os.path.exists(POOL_FILE):
        try:
            with open(POOL_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_pool(p):
    try:
        with open(POOL_FILE, "w", encoding="utf-8") as f:
            json.dump(p, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving pool: {e}")

pool = load_pool()

async def fetch_config():
    global DOMAIN
    async with ClientSession(headers={"X-API-Key": API_KEY}) as session:
        async with session.get(f"{API_BASE}/api/config") as resp:
            if resp.status == 200:
                data = await resp.json()
                domains = data.get("emailDomains", "").split(",")
                if domains and not DOMAIN:
                    DOMAIN = domains[0].strip()

async def generate_email():
    async with ClientSession(headers={"X-API-Key": API_KEY}) as session:
        payload = {"domain": DOMAIN, "expiryTime": 3600000}
        async with session.post(f"{API_BASE}/api/emails/generate", json=payload) as resp:
            if resp.status == 200:
                data = await resp.json()
                return {"id": data["id"], "address": data["email"], "created_at": time.time()}
    return None

async def handle_get_email(request):
    global pool
    now = time.time()
    pool = [e for e in pool if now - e["created_at"] < 3500]
    if not pool:
        new_mail = await generate_email()
        if new_mail:
            pool.append(new_mail)
            save_pool(pool)
        else:
            return web.json_response({"error": "Failed to generate email"}, status=500)
    mail = pool.pop(0)
    save_pool(pool)
    return web.json_response(mail)

async def handle_get_code(request):
    email_id = request.match_info.get("id")
    pattern = request.query.get("pattern", r"\b\d{4,6}\b")
    async with ClientSession(headers={"X-API-Key": API_KEY}) as session:
        for _ in range(15):
            async with session.get(f"{API_BASE}/api/emails/{email_id}") as resp:
                if resp.status == 200:
                    messages = await resp.json()
                    if isinstance(messages, list) and messages:
                        msg_id = messages[0].get("id")
                        async with session.get(f"{API_BASE}/api/emails/{email_id}/{msg_id}") as msg_resp:
                            if msg_resp.status == 200:
                                msg_data = await msg_resp.json()
                                content = msg_data.get("text", "") or msg_data.get("html", "") or msg_data.get("subject", "")
                                match = re.search(pattern, content)
                                if match:
                                    return web.json_response({"code": match.group(0), "subject": msg_data.get("subject")})
            await asyncio.sleep(2)
    return web.json_response({"error": "Timeout waiting for code"}, status=408)

app = web.Application()
app.router.add_get("/mail", handle_get_email)
app.router.add_get("/mail/{id}/code", handle_get_code)

if __name__ == "__main__":
    web.run_app(app, port=8080)
