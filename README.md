# Fantasy Baseball Waiver Wire Bot

Scrapes the CBS Sports fantasy baseball waiver wire column every Thursday morning, gets an AI-powered add/drop recommendation from Claude, and texts it to you via Twilio.

## What it does

1. Scrapes `cbssports.com/fantasy/baseball/` to find the latest waiver wire article
2. Extracts the "Thursday's top waiver-wire targets" and "Wednesday's standouts" sections
3. Sends the content to Claude (`claude-sonnet-4-20250514`) for a concise add/drop analysis
4. Texts the response to your phone via Twilio

## Setup

### 1. Clone and install dependencies

```bash
git clone <your-repo>
cd waiver-wire-bot
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in:

| Variable | Where to get it |
|---|---|
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) |
| `TWILIO_ACCOUNT_SID` | [console.twilio.com](https://console.twilio.com) → Account Info |
| `TWILIO_AUTH_TOKEN` | Same page as above |
| `TWILIO_FROM_NUMBER` | Your Twilio phone number (E.164 format, e.g. `+15005550006`) |
| `TO_PHONE_NUMBER` | Your cell number (E.164 format, e.g. `+12025551234`) |

### 3. Run locally

```bash
python waiver_wire.py
```

## Deploy to Render

### Prerequisites
- A [Render](https://render.com) account
- Your code pushed to a GitHub or GitLab repository

### Steps

1. Push this repo to GitHub
2. In Render, click **New → Blueprint**
3. Connect your repository — Render will detect `render.yaml` automatically
4. Click **Apply** and enter your five environment variable values when prompted
5. The cron job will appear under **Cron Jobs** and run every Thursday at 8:00 AM ET

### Manual trigger

From the Render dashboard, open the cron job and click **Trigger Run** to test it immediately.

## Cron schedule

```
0 13 * * 4
```

Runs every **Thursday at 13:00 UTC = 8:00 AM ET** (9:00 AM EDT during daylight saving time — adjust to `0 12 * * 4` in summer if you want exactly 8am EDT).

## Error handling

- If the CBS Sports article isn't posted yet, you'll receive: *"Waiver wire column not found yet, check CBS Sports manually"*
- If the article is found but sections can't be extracted, you'll receive the article URL directly
- AI responses longer than 1,600 characters are truncated at the last complete sentence

## Project structure

```
waiver_wire.py     # Main script
requirements.txt   # Python dependencies
render.yaml        # Render Blueprint (cron job config)
.env.example       # Environment variable template
README.md          # This file
```
