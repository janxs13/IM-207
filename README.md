# BusBook - Bus Booking System

A web application for booking bus rides built with Flask and SQLite.

## Features

- User booking and seat selection
- Multiple payment methods (GCash, PayMaya, PayPal, PayMongo)
- QR code ticket generation
- Admin dashboard for managing buses, schedules, and bookings
- Ticket verification system

## Setup Instructions

### 1. Create Virtual Environment
```powershell
python -m venv venv
```

### 2. Install Dependencies
```powershell
venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 3. Run the App
```powershell
venv\Scripts\python.exe app.py
```

### 4. Open in Browser
Go to: http://127.0.0.1:5000

## Default Login (Demo)

After registering a new account, an admin can manually set the role to "admin" in the database.

Or use the admin panel at `/admin` (requires admin role).

## Project Structure

```
IM-207/
├── app.py              # Main Flask application
├── config.py           # Configuration settings
├── requirements.txt   # Python dependencies
├── .env             # Environment variables (create from .env.example)
├── models/          # Database models
├── routes/          # API routes
├── services/        # Business logic
├── sockets/        # Real-time functionality
├── static/         # CSS, JS, images
├── templates/      # HTML templates
└── utils/        # Helper functions
```

## Troubleshooting

**Missing modules error:**
```powershell
venv\Scripts\python.exe -m pip install -r requirements.txt
```

**App won't start:**
Check that port 5000 is not in use, or change the port in app.py.
