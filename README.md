# ⚡ ZENOVA TECH — Telegram Forwarder Pro
## Complete Setup Guide: Supabase + Railway + Vercel

---

## 📁 Project Structure
```
zenova-forwarder/
├── backend/
│   ├── bot.py              ← Python bot (deploy to Railway)
│   ├── requirements.txt    ← Python dependencies
│   ├── Procfile            ← Railway process config
│   └── .env.example        ← Environment variables template
├── frontend/
│   ├── index.html          ← Dashboard UI (deploy to Vercel)
│   └── vercel.json         ← Vercel config
└── supabase/
    └── schema.sql          ← Database tables (run in Supabase)
```

---

## STEP 1 — SUPABASE SETUP (10 minutes)

1. Go to https://supabase.com → Sign up (free)
2. Click **New Project** → name it `zenova-forwarder`
3. Choose a region close to you → Create project
4. Wait ~2 minutes for project to be ready
5. Go to **SQL Editor** (left sidebar)
6. Click **New Query**
7. Copy ALL contents of `supabase/schema.sql` → Paste → Click **Run**
8. You should see: "Success. No rows returned"

### Get your Supabase credentials:
- Go to **Settings** → **API**
- Copy **Project URL** → looks like `https://abcxyz.supabase.co`
- Copy **anon public** key → long string starting with `eyJ...`

---

## STEP 2 — RAILWAY SETUP (10 minutes)

1. Go to https://railway.app → Sign up with GitHub
2. Click **New Project** → **Deploy from GitHub repo**
3. Create a new GitHub repo and upload your `backend/` folder contents:
   - `bot.py`
   - `requirements.txt`
   - `Procfile`
4. Connect that repo to Railway
5. Go to your Railway project → **Variables** tab
6. Add these 2 variables:
   ```
   SUPABASE_URL = https://your-project-id.supabase.co
   SUPABASE_KEY = your-anon-key
   ```
7. Go to **Settings** → make sure **Worker** is selected (not Web)
8. Railway will auto-deploy and run `python bot.py`

### ⚠️ First Run — OTP Required:
When bot runs for the first time, it needs OTP for each Telegram account.
Check Railway logs → it will show a prompt.
You'll need to temporarily add a way to input OTP (or run locally first to generate sessions, then upload session files to Railway).

### Recommended: Run locally first
```bash
pip install telethon supabase
python bot.py
# Enter OTP for each account when prompted
# This creates account1.session, account2.session, account3.session files
# Upload these session files to Railway too
```

---

## STEP 3 — VERCEL SETUP (5 minutes)

1. Go to https://vercel.com → Sign up with GitHub
2. Open `frontend/index.html`
3. Find these 2 lines near the bottom and replace with your real values:
   ```js
   const SUPABASE_URL  = 'https://your-project-id.supabase.co';  // ← replace
   const SUPABASE_ANON = 'your-anon-key';                         // ← replace
   ```
4. Create a new GitHub repo → upload `frontend/` folder contents:
   - `index.html`
   - `vercel.json`
5. Go to Vercel → **New Project** → Import that repo
6. Click **Deploy**
7. Vercel gives you a live URL like `https://zenova-forwarder.vercel.app`

---

## STEP 4 — FINAL TEST

1. Open your Vercel URL in browser
2. Go to ⚙️ Settings tab
3. Enter your API credentials, groups, source channel
4. Click 💾 Save & Apply
5. Go to Railway → manually trigger a deploy or restart
6. Watch the 📊 Dashboard — logs should appear in real time!

---

## HOW IT ALL CONNECTS

```
You open Dashboard (Vercel URL)
        ↓
Enter settings → saved to Supabase database
        ↓
Python bot (Railway) reads settings from Supabase
        ↓
Bot forwards messages every 50s to all 9 groups
        ↓
Bot writes each log entry to Supabase
        ↓
Dashboard receives live updates via Supabase Realtime
        ↓
You see live stats, logs, success rate in real time ✅
```

---

## COSTS

| Service | Free Tier | Paid |
|---------|-----------|------|
| Supabase | 500MB DB, 2GB bandwidth | $25/mo |
| Railway | $5 free credit/mo | ~$5-10/mo |
| Vercel | Unlimited static sites | Free |
| **Total** | **~Free to start** | **~$5-10/mo** |

---

## SUPPORT
Built by ⚡ Zenova Tech
