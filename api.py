from fastapi import FastAPI
from telethon import TelegramClient
import os

app = FastAPI()

API_ID = int(os.environ["TG_API_ID"])
API_HASH = os.environ["TG_API_HASH"]

clients = {}

@app.post("/telegram/send-otp")
async def send_otp(phone: str):
    client = TelegramClient(f"sessions/{phone}", API_ID, API_HASH)
    await client.connect()
    await client.send_code_request(phone)
    clients[phone] = client
    return {"status": "otp_sent"}

@app.post("/telegram/verify-otp")
async def verify_otp(phone: str, code: str):
    client = clients.get(phone)
    await client.sign_in(phone, code)
    return {"status": "logged_in"}
