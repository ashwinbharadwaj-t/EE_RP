# Estonia New Delhi residence-permit slot watcher

Watches the Estonian MFA consular booking page. When "Application for
Residence Permit" becomes selectable for the New Delhi embassy, it sends
you a Telegram push. Runs on GitHub Actions (in the cloud), so nothing runs
on your laptop.

## One-time setup (browser only, ~10 min)

### 1. Regenerate your Telegram token
Your old token was exposed in chat, so revoke it first:
- Telegram -> @BotFather -> send `/revoke` -> pick your bot -> copy the NEW token.
Also get your numeric chat id from @userinfobot (message it, it replies with your Id).

### 2. Put these files in a GitHub repo
- Create a new repository (private is fine) at github.com.
- Add these files with the SAME folder layout:
  - `check.py`
  - `.github/workflows/watch.yml`
  - `README.md`
  You can do this via the web UI: "Add file" -> "Create new file", and for the
  workflow, type the path `.github/workflows/watch.yml` as the filename.

### 3. Add your secrets (never put the token in the code)
Repo -> Settings -> Secrets and variables -> Actions -> New repository secret:
- `TG_TOKEN`   = your new bot token
- `TG_CHAT_ID` = your numeric chat id

### 4. Turn it on
- Repo -> Actions tab -> enable workflows if prompted.
- Open "estonia-slot-watch" -> "Run workflow" to test immediately.
- You should get a Telegram "heartbeat" message listing the dropdown options
  it saw. That confirms it's reading the right dropdown.

### 5. Silence the heartbeats (optional, after confirming)
Once you've confirmed it reads the right dropdown, set `DEBUG_LIST: "false"`
in `.github/workflows/watch.yml`. Then it stays quiet until the residence
permit option actually appears.

## Notes
- Schedule is every 20 min. Change the `cron` line in watch.yml to adjust.
- It only NOTIFIES. You book manually. It never grabs or holds a slot.
- If the site layout changes and it can't find the dropdown, it messages you
  so you know to check.
