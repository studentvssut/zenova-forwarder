import asyncio
import os
import time
from datetime import datetime

from telethon import TelegramClient, errors
from supabase import create_client, Client

# ======================================================
# ENV (SAFE MODE)
# ======================================================
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client | None = None

if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Supabase client initialized", flush=True)
    except Exception as e:
        print("❌ Supabase init failed:", e, flush=True)
else:
    print("⚠️ Supabase env vars missing. Running in WAIT mode.", flush=True)

# ======================================================
# GLOBALS
# ======================================================
clients = []
account_index = 0


# ======================================================
# SUPABASE HELPERS (SAFE)
# ======================================================
def sb_available():
    return supabase is not None


def get_settings():
    if not sb_available():
        return None
    return supabase.table("settings").select("*").eq("id", 1).single().execute().data


def get_accounts():
    if not sb_available():
        return []
    res = supabase.table("accounts").select("*").order("account_number").execute().data
    return [a for a in res if a.get("api_id") and a.get("api_hash") and a.get("phone")]


def get_groups():
    if not sb_available():
        return []
    res = supabase.table("groups").select("*").order("group_number").execute().data
    return [g["group_name"] for g in res if g.get("group_name")]


def update_stats(rounds, success, failed):
    if not sb_available():
        return
    supabase.table("stats").update({
        "total_rounds": rounds,
        "total_success": success,
        "total_failed": failed,
        "updated_at": datetime.utcnow().isoformat()
    }).eq("id", 1).execute()


def write_log(round_num, group, acc_num, status, message):
    if not sb_available():
        return
    supabase.table("logs").insert({
        "round_number": round_num,
        "group_name": group,
        "account_number": acc_num,
        "status": status,
        "message": message,
        "created_at": datetime.utcnow().isoformat()
    }).execute()


# ======================================================
# TELEGRAM
# ======================================================
async def init_clients(accounts):
    global clients
    clients = []

    for acc in accounts:
        client = TelegramClient(
            f"/tmp/session_{acc['account_number']}",
            int(acc["api_id"]),
            acc["api_hash"]
        )
        await client.start(phone=acc["phone"])
        print(f"✅ Logged in: {acc['phone']}", flush=True)
        clients.append(client)


def get_next_client():
    global account_index
    idx = account_index % len(clients)
    account_index += 1
    return clients[idx], idx + 1


# ======================================================
# FORWARD ROUND
# ======================================================
async def forward_round(round_num, groups, source, message_id, stats):
    print(f"\n🔁 Round {round_num}", flush=True)

    for group in groups:
        client, acc_num = get_next_client()

        try:
            await client.forward_messages(group, int(message_id), source)
            stats["success"] += 1
            msg = f"✅ → {group} via Acc{acc_num}"
            write_log(round_num, group, acc_num, "success", msg)
            print(msg, flush=True)

        except errors.FloodWaitError as e:
            wait = int(e.seconds) + 5
            print(f"⏳ FloodWait {wait}s (Acc{acc_num})", flush=True)
            await asyncio.sleep(wait)

        except Exception as e:
            stats["failed"] += 1
            msg = f"❌ → {group} ERROR: {str(e)[:80]}"
            write_log(round_num, group, acc_num, "failed", msg)
            print(msg, flush=True)

        await asyncio.sleep(1)

    update_stats(round_num, stats["success"], stats["failed"])


# ======================================================
# MAIN LOOP (NEVER DIES)
# ======================================================
async def main():
    print("🚀 Zenova Forwarder Worker started", flush=True)

    while True:
        try:
            if not sb_available():
                print("⏳ Waiting for valid Supabase env vars...", flush=True)
                await asyncio.sleep(15)
                continue

            settings = get_settings()
            accounts = get_accounts()
            groups = get_groups()

            if not settings:
                print("⚠️ Settings row missing (id=1)", flush=True)
                await asyncio.sleep(10)
                continue

            if not accounts or not groups:
                print("⚠️ Waiting for accounts / groups...", flush=True)
                await asyncio.sleep(10)
                continue

            await init_clients(accounts)

            source = settings["source_channel"]
            message_id = settings["message_id"]
            interval = settings["interval_seconds"]

            stats = {"success": 0, "failed": 0}
            round_num = 0

            print("🟢 Worker RUNNING", flush=True)

            while True:
                fresh = get_settings()
                if fresh and not fresh.get("is_running", True):
                    print("⏸ Paused from dashboard", flush=True)
                    await asyncio.sleep(5)
                    continue

                round_num += 1
                await forward_round(round_num, groups, source, message_id, stats)
                await asyncio.sleep(interval)

        except Exception as e:
            print("🔥 Worker error (safe restart):", e, flush=True)
            await asyncio.sleep(5)


# ======================================================
if __name__ == "__main__":
    asyncio.run(main())
