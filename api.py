from fastapi import FastAPI
from pydantic import BaseModel
from telethon import TelegramClient
import os

app = FastAPI()

API_ID = int(os.environ["TG_API_ID"])
API_HASH = os.environ["TG_API_HASH"]

# ───────────────
# Request Models
# ───────────────
class SendOTPRequest(BaseModel):
    phone: str

class VerifyOTPRequest(BaseModel):
    phone: str
    code: str

clients = {}

# ───────────────
# Send OTP
# ───────────────
@app.post("/telegram/send-otp")
async def send_otp(data: SendOTPRequest):
    phone = data.phone

    # ✅ FIX: Railway-safe session path
    client = TelegramClient(f"/tmp/session_{phone}", API_ID, API_HASH)

    await client.connect()
    await client.send_code_request(phone)

    clients[phone] = client
    return {"status": "otp_sent"}

# ───────────────
# Verify OTP
# ───────────────
@app.post("/telegram/verify-otp")
async def verify_otp(data: VerifyOTPRequest):
    phone = data.phone
    code = data.code

    client = clients.get(phone)
    if not client:
        return {"error": "OTP not requested"}

    await client.sign_in(phone, code)
    await client.disconnect()  # ✅ cleanup

    return {"status": "logged_in"}
