import threading
import time
import sqlite3
import os
from flask import Flask, render_template
from config import Config
from extensions import db, jwt, socketio

from routes.auth_routes     import auth_bp
from routes.schedule_routes import schedule_bp
from routes.booking_routes  import booking_bp
from routes.payment_routes  import payment_bp
from routes.admin_routes    import admin_bp
from routes.verify_routes   import verify_bp
from routes.ticket_routes   import ticket_bp

from models.user     import User
from models.bus      import Bus
from models.schedule import Schedule
from models.booking  import Booking
from models.payment  import Payment


def _safe_migrate(app):
    """Add any missing columns to the existing SQLite DB without losing data."""
    db_path = os.path.join(app.instance_path, "bus_ticketing.db")
    if not os.path.exists(db_path):
        return  # fresh DB — db.create_all() will build everything

    conn = sqlite3.connect(db_path)
    cur  = conn.cursor()

    def col_exists(table, col):
        cur.execute(f"PRAGMA table_info({table})")
        return any(r[1] == col for r in cur.fetchall())

    pending = [
        ("user", "reset_token", "ALTER TABLE user ADD COLUMN reset_token VARCHAR(20)"),
    ]

    for table, col, sql in pending:
        try:
            if not col_exists(table, col):
                cur.execute(sql)
                conn.commit()
                print(f"[migrate] Added column {table}.{col}")
        except Exception as e:
            print(f"[migrate] Warning: {e}")

    conn.close()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    jwt.init_app(app)
    socketio.init_app(app)

    # ── API blueprints ──────────────────────────────────────────────
    app.register_blueprint(auth_bp,     url_prefix="/api/auth")
    app.register_blueprint(schedule_bp, url_prefix="/api/schedules")
    app.register_blueprint(booking_bp,  url_prefix="/api/bookings")
    app.register_blueprint(payment_bp,  url_prefix="/api/payments")
    app.register_blueprint(admin_bp,    url_prefix="/api/admin")
    app.register_blueprint(verify_bp,   url_prefix="/api/verify")
    app.register_blueprint(ticket_bp,   url_prefix="/api/ticket")

    # ── Public / Auth pages ─────────────────────────────────────────
    @app.route("/")
    def home():               return render_template("user/index.html")

    @app.route("/login")
    def login_page():         return render_template("user/login.html")

    @app.route("/register")
    def register_page():      return render_template("register.html")

    @app.route("/forgot-password")
    def forgot_password_page(): return render_template("user/forgot-password.html")

    # ── Passenger pages ─────────────────────────────────────────────
    @app.route("/book")
    def book_page():          return render_template("user/book.html")

    @app.route("/seat-selection")
    def seat_page():          return render_template("user/seat-selection.html")

    @app.route("/transaction")
    def transaction_page():   return render_template("user/transaction.html")

    @app.route("/ticket")
    def ticket_page():        return render_template("user/ticket.html")

    @app.route("/profile")
    def profile_page():       return render_template("user/profile.html")

    @app.route("/routes")
    def routes_page():        return render_template("user/routes.html")

    @app.route("/contact")
    def contact_page():       return render_template("user/contact.html")

    @app.route("/about")
    def about_page():         return render_template("user/about.html")

    @app.route("/receipt")
    def receipt_page():       return render_template("user/receipt.html")

    @app.route("/gcash")
    def gcash_page():         return render_template("user/gcash.html")

    @app.route("/paymaya")
    def paymaya_page():       return render_template("user/paymaya.html")

    @app.route("/paypal")
    def paypal_page():        return render_template("user/paypal.html")

    # ── Admin pages ─────────────────────────────────────────────────
    @app.route("/admin")
    def admin_dashboard():    return render_template("admin/admindashboard.html")

    @app.route("/admin/users")
    def admin_users():        return render_template("admin/manage-users.html")

    @app.route("/admin/schedule")
    def admin_schedule():     return render_template("admin/manage-schedule.html")

    @app.route("/admin/buses")
    def admin_buses():        return render_template("admin/manage-buses.html")

    @app.route("/admin/verify")
    def admin_verify():       return render_template("admin/verify-ticket.html")

    @app.route("/admin/revenue")
    def admin_revenue():      return render_template("admin/revenue.html")

    @app.route("/admin/bookings-report")
    def admin_bookings_report(): return render_template("admin/bookings-report.html")

    # ── Error handlers ──────────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):         return render_template("user/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):      return render_template("user/404.html"), 500

    with app.app_context():
        _safe_migrate(app)   # add missing columns BEFORE create_all
        db.create_all()      # create any brand-new tables

    return app


def cleanup_job(app):
    while True:
        with app.app_context():
            from services.seat_cleanup_service import release_expired_seats
            release_expired_seats()
        time.sleep(60)


app = create_app()

cleanup_thread = threading.Thread(target=cleanup_job, args=(app,), daemon=True)
cleanup_thread.start()

if __name__ == "__main__":
    socketio.run(app, debug=True)
