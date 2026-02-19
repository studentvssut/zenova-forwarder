"""
=======================================================
  ZENOVA TECH — Telegram Forwarder Pro
  Backend Bot — Supabase + Telethon
=======================================================
  Reads config from Supabase
  Writes logs/stats back to Supabase
  Runs on Railway
=======================================================
"""

import asyncio
import os
from datetime import datetime
from telethon import TelegramClient
from supabase import create_client, Client

# ── SUPABASE CONFIG (set these in Railway environment variables) ──
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ── GLOBALS ──
clients = []
account_index = 0
is_running = False


# ══════════════════════════════
#  SUPABASE HELPERS
# ══════════════════════════════

def get_settings():
    res = supabase.table("settings").select("*").eq("id", 1).single().execute()
    return res.data

def get_accounts():
    res = supabase.table("accounts").select("*").order("account_number").execute()
    return [a for a in res.data if a["api_id"] and a["api_hash"] and a["phone"]]

def get_groups():
    res = supabase.table("groups").select("*").order("group_number").execute()
    return [g["group_name"] for g in res.data if g["group_name"]]

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

def set_running(state: bool):
    supabase.table("settings").update({
        "is_running": state,
        "updated_at": datetime.utcnow().isoformat()
    }).eq("id", 1).execute()


# ══════════════════════════════
#  TELETHON SETUP
# ══════════════════════════════

async def init_clients(accounts):
    global clients
    clients = []
    for acc in accounts:
        client = TelegramClient(
            f"session_{acc['account_number']}",
            int(acc["api_id"]),
            acc["api_hash"]
        )
        await client.start(phone=acc["phone"])
        print(f"✅ Logged in: {acc['phone']}")
        clients.append(client)

def get_next_client():
    global account_index
    idx = account_index % len(clients)
    client = clients[idx]
    account_index += 1
    return client, idx + 1


# ══════════════════════════════
#  FORWARD ROUND
# ══════════════════════════════

async def forward_round(round_num, groups, source, message_id, stats):
    print(f"\n🔁 Round {round_num}")
    for group in groups:
        client, acc_num = get_next_client()
        try:
            await client.forward_messages(group, int(message_id), source)
            stats["success"] += 1
            msg = f"✅ → {group} via Acc{acc_num}"
            write_log(round_num, group, acc_num, "success", msg)
            print(msg)
        except Exception as e:
            stats["failed"] += 1
            msg = f"❌ → {group} ERROR: {str(e)[:60]}"
            write_log(round_num, group, acc_num, "failed", msg)
            print(msg)
        await asyncio.sleep(1)

    update_stats(round_num, stats["success"], stats["failed"])


# ══════════════════════════════
#  MAIN LOOP
# ══════════════════════════════

async def main():
    global is_running

    print("🚀 Zenova Tech — Telegram Forwarder starting...")

    # Load config from Supabase
    settings = get_settings()
    accounts = get_accounts()
    groups   = get_groups()

    if not accounts:
        print("❌ No accounts configured in Supabase. Add them via the dashboard.")
        return
    if not groups:
        print("❌ No groups configured in Supabase. Add them via the dashboard.")
        return

    source      = settings["source_channel"]
    message_id  = settings["message_id"]
    interval    = settings["interval_seconds"]
    duration    = settings["duration_hours"] * 3600
    total_rounds = int(duration / interval)

    print(f"   Source   : {source}")
    print(f"   Message  : {message_id}")
    print(f"   Groups   : {len(groups)}")
    print(f"   Accounts : {len(accounts)}")
    print(f"   Interval : {interval}s")
    print(f"   Duration : {settings['duration_hours']}h ({total_rounds} rounds)\n")

    await init_clients(accounts)
    set_running(True)

    # Reset stats
    supabase.table("stats").update({
        "total_rounds": 0,
        "total_success": 0,
        "total_failed": 0,
        "started_at": datetime.utcnow().isoformat()
    }).eq("id", 1).execute()

    stats = {"success": 0, "failed": 0}
    import time
    end_time = time.time() + duration

    round_num = 0
    while time.time() < end_time:
        # Check if paused from dashboard
        fresh = get_settings()
        if not fresh["is_running"]:
            print("⏸ Paused from dashboard. Waiting...")
            await asyncio.sleep(5)
            continue

        round_num += 1
        await forward_round(round_num, groups, source, message_id, stats)

        elapsed = time.time() - (end_time - duration)
        remaining = end_time - time.time()
        print(f"   ✅ {stats['success']} | ❌ {stats['failed']} | ⏳ {int(remaining//60)}m remaining")
        await asyncio.sleep(interval)

    set_running(False)
    print("\n🏁 3-hour run complete!")
    print(f"   Total Success : {stats['success']}")
    print(f"   Total Failed  : {stats['failed']}")

    for client in clients:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
