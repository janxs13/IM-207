# IM-207 BusBook

Bus booking website (Passenger + Admin) built with Flask, Flask-SocketIO, and SQLite.

This guide is focused on running your **updated website from your laptop** and opening it from **another PC on the same network**.

## 1) Requirements

- Windows 10/11
- Python 3.12+ (your project currently uses Python 3.14 in `venv`)
- Git (optional, for pulling updates)

## 2) First-time setup (on the host laptop)

From project root:

```powershell
python -m venv venv
venv\Scripts\python.exe -m pip install --upgrade pip
venv\Scripts\python.exe -m pip install -r requirements.txt
```

Create your env file:

```powershell
copy .env.example .env
```

Then edit `.env` with real values (`SECRET_KEY`, `JWT_SECRET_KEY`, mail settings if needed).

## 3) Database notes

- Default DB is SQLite (`instance/bus_ticketing.db`).
- Your app auto-creates missing tables/columns at startup.
- If this is the same project folder you already use, your data stays intact.

## 4) Run locally (quick check)

```powershell
venv\Scripts\python.exe app.py
```

Open on the host laptop:

- [http://127.0.0.1:5000](http://127.0.0.1:5000)

## 5) Run so another PC can open it (same Wi-Fi/LAN)

### A. Start server bound to all interfaces

Use this PowerShell command from project root:

```powershell
venv\Scripts\python.exe -c "from app import app, socketio; socketio.run(app, host='0.0.0.0', port=5000, debug=True)"
```

### B. Find host laptop IP

```powershell
ipconfig
```

Use the IPv4 address of your active adapter (example: `192.168.1.15`).

### C. Open Windows Firewall (if blocked)

Allow inbound TCP port `5000` for Private network.

### D. Open from another PC

On the second PC browser:

- `http://<HOST_IP>:5000`
- Example: [http://192.168.1.15:5000](http://192.168.1.15:5000)

## 6) Keep code updated on another PC

If both PCs have this repository, update with:

```powershell
git pull
venv\Scripts\python.exe -m pip install -r requirements.txt
```

Then run the same LAN command above.

## 7) One-command health check (added)

Before running in front of users, validate the app:

```powershell
scan.bat
```

It runs:

- Ruff lint
- Pytest smoke tests
- Python compile checks
- Flask app import/route smoke check

## 8) Common issues

- **Site opens on laptop but not on second PC**
  - Server is likely running on `127.0.0.1` only. Use the LAN command with `host='0.0.0.0'`.
- **Connection timed out**
  - Wrong IP, different network, or firewall blocking port `5000`.
- **QR scan opens wrong URL**
  - Ensure admin verifies from `/admin/verify` (or `/verify/<code>` redirect flow).
- **Missing package error**
  - Re-run `venv\Scripts\python.exe -m pip install -r requirements.txt`.

---

If you want, I can also add a dedicated `run_lan.bat` so you don't need to type the long LAN command each time.
