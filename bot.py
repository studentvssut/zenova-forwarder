import asyncio
import os
from datetime import datetime

from telethon import TelegramClient, errors
from supabase import create_client, Client

# ======================================================
# GLOBALS
# ======================================================
supabase: Client | None = None
clients = []
account_index = 0


# ======================================================
# SUPABASE INIT (FIX)
# ======================================================
def init_supabase():
    global supabase

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        supabase = None
        return False

    try:
        supabase = create_client(url, key)
        return True
    except Exception as e:
        print("❌ Supabase init failed:", e, flush=True)
        supabase = None
        return False


def sb_available():
    return supabase is not None


# ======================================================
# SUPABASE HELPERS
# ======================================================
def get_settings():
    return supabase.table("settings").select("*").eq("id", 1).single().execute().data


def get_accounts():
    res = supabase.table("accounts").select("*").order("account_number").execute().data
    return [a for a in res if a.get("api_id") and a.get("api_hash") and a.get("phone")]


def get_groups():
    res = supabase.table("groups").select("*").order("group_number").execute().data
    return [g["group_name"] for g in res if g.get("group_name")]


def update_stats(rounds, success, failed):
    supabase.table("stats").update({
        "total_rounds": rounds,
        "total_success": success,
        "total_failed": failed,
        "updated_at": datetime.utcnow().isoformat()
    }).eq("id", 1).execute()


def write_log(round_num, group, acc_num, status, message):
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
# MAIN LOOP (RECOVERABLE)
# ======================================================
async def main():
    print("🚀 Zenova Forwarder Worker started", flush=True)

    while True:
        try:
            if not init_supabase():
                print("⏳ Waiting for Supabase env vars...", flush=True)
                await asyncio.sleep(10)
                continue

            print("✅ Supabase connected", flush=True)

            settings = get_settings()
            accounts = get_accounts()
            groups = get_groups()

            if not settings or not accounts or not groups:
                print("⚠️ Waiting for DB configuration...", flush=True)
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
                if not fresh.get("is_running", True):
                    print("⏸ Paused from dashboard", flush=True)
                    await asyncio.sleep(5)
                    continue

                round_num += 1
                await forward_round(round_num, groups, source, message_id, stats)
                await asyncio.sleep(interval)

        except Exception as e:
            print("🔥 Worker error, restarting safely:", e, flush=True)
            await asyncio.sleep(5)


# ======================================================
if __name__ == "__main__":
    asyncio.run(main())
