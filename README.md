# IM-207 BusBook

Bus booking web app (Passenger + Admin) built with Flask, Flask-SocketIO, and SQLite.

## Quick Start (3 commands)

Run these in project root:

```powershell
python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt
venv\Scripts\python.exe app.py
```

Then open [http://127.0.0.1:5000](http://127.0.0.1:5000).

## Step-by-step setup instructions

## 1) Prerequisites

- Windows 10/11
- Python 3.12+ (project currently uses Python 3.14 in `venv`)
- Git (optional)

## 2) Clone or open project folder

If needed:

```powershell
git clone <your-repo-url>
cd IM-207
```

If you already have the folder, just open `E:\IM-207`.

## 3) Create virtual environment

From project root:

```powershell
python -m venv venv
```

## 4) Install dependencies

```powershell
venv\Scripts\python.exe -m pip install --upgrade pip
venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 5) Configure environment variables

Create your `.env` file:

```powershell
copy .env.example .env
```

Then edit `.env` and set real values such as:

- `SECRET_KEY`
- `JWT_SECRET_KEY`
- Mail settings (if using password reset/contact email)

## 6) Database setup

- Default database: `instance/bus_ticketing.db`
- Tables are created automatically on app start.
- Missing columns are migrated automatically by `_safe_migrate()` in `app.py`.

## 7) Run the app locally

```powershell
venv\Scripts\python.exe app.py
```

Open in browser:

- [http://127.0.0.1:5000](http://127.0.0.1:5000)

## 8) Run app for other devices on same network (LAN)

Start server on all interfaces:

```powershell
venv\Scripts\python.exe -c "from app import app, socketio; socketio.run(app, host='0.0.0.0', port=5000, debug=True)"
```

Get your host machine IPv4 address:

```powershell
ipconfig
```

From another device, open:

- `http://<HOST_IP>:5000`
- Example: [http://192.168.1.15:5000](http://192.168.1.15:5000)

If blocked, allow inbound TCP `5000` in Windows Firewall (Private network).

## 9) Run one-command health scan (lint + tests + smoke checks)

```powershell
scan.bat
```

This runs:

- Ruff lint checks
- Pytest smoke tests
- Python compile checks
- Flask import/route smoke check

## 10) Admin and ticket verification notes

- Admin dashboard: `/admin`
- Admin verify page: `/admin/verify`
- QR links using `/verify/<code>` are supported and auto-redirect to admin verify.

## 11) Update project later

```powershell
git pull
venv\Scripts\python.exe -m pip install -r requirements.txt
scan.bat
```

## 12) Troubleshooting

- App opens on laptop but not other devices:
  - Run with `host='0.0.0.0'` (LAN mode), not default localhost-only mode.
- Missing module error:
  - Re-run `venv\Scripts\python.exe -m pip install -r requirements.txt`.
- QR scan/verify issues:
  - Verify from `/admin/verify` and ensure camera permission is allowed.
