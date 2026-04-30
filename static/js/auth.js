/* ==========================================================
   BusBook — auth.js  (Phase 4 final)
   Shared: token management, logout, Toast, form validation
   ========================================================== */

const Auth = {
  getToken()  { return localStorage.getItem('access_token') || localStorage.getItem('authToken'); },
  getUser()   { try { return JSON.parse(localStorage.getItem('currentUser') || 'null'); } catch { return null; } },

  saveSession(token, user) {
    localStorage.setItem('access_token', token);
    localStorage.setItem('authToken',    token);   // backward compat
    localStorage.setItem('currentUser',  JSON.stringify(user));
  },

  clearSession() {
    ['access_token','authToken','currentUser','currentBooking','currentSchedule',
     'selectedFrom','selectedTo','selectedPrice','receiptPayment','receiptRef',
     'receiptAmount','passengerCount','selectedSeats','lastBookingCode','farePerSeat'].forEach(k => localStorage.removeItem(k));
  },

  headers(extra = {}) {
    return { 'Content-Type': 'application/json', 'Authorization': `Bearer ${this.getToken()}`, ...extra };
  },

  requireLogin(redirectTo = '/login') {
    if (!this.getToken()) { window.location.href = redirectTo; return false; }
    return true;
  },

  requireAdmin() {
    const user = this.getUser();
    if (!user || user.role !== 'admin') { window.location.href = '/login'; return false; }
    return true;
  },

  redirectIfLoggedIn(to = '/book') {
    if (this.getToken()) window.location.href = to;
  },

  logout() { this.clearSession(); window.location.href = '/login'; },

  renderSidebarUser(nameId = 'sidebarUserName', avatarId = 'sidebarAvatar') {
    const user = this.getUser();
    if (!user) return;
    const name = user.username || user.first_name || user.email || 'Admin';
    const el1 = document.getElementById(nameId);
    const el2 = document.getElementById(avatarId);
    if (el1) el1.textContent = name;
    if (el2) el2.textContent = name[0].toUpperCase();
  }
};

/* ── Toast notification system ──────────────────────────── */
const Toast = {
  show(message, type = 'default', duration = 3800) {
    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      document.body.appendChild(container);
    }

    const icons = {
      success: '<i class="fa-solid fa-circle-check"></i>',
      error:   '<i class="fa-solid fa-circle-xmark"></i>',
      warning: '<i class="fa-solid fa-triangle-exclamation"></i>',
      default: '<i class="fa-solid fa-bell"></i>'
    };

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `${icons[type] || icons.default} <span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.animation = 'slideOut 0.25s ease forwards';
      setTimeout(() => toast.remove(), 260);
    }, duration);
  },
  success(msg, dur)  { this.show(msg, 'success', dur); },
  error(msg, dur)    { this.show(msg, 'error', dur); },
  warning(msg, dur)  { this.show(msg, 'warning', dur); }
};

/* ── Form validation helpers ─────────────────────────────── */
const Validate = {
  /** Mark a field as errored with inline message */
  error(inputId, message) {
    const input = document.getElementById(inputId);
    if (!input) return;
    input.style.borderColor = 'var(--red)';
    input.style.boxShadow   = '0 0 0 3px rgba(239,68,68,0.15)';
    // Remove existing error
    const existing = input.parentNode.querySelector('.field-error');
    if (existing) existing.remove();
    const err = document.createElement('div');
    err.className = 'field-error';
    err.style.cssText = 'font-size:12px;color:var(--red);margin-top:4px;display:flex;align-items:center;gap:4px;';
    err.innerHTML = `<i class="fa-solid fa-circle-exclamation"></i> ${message}`;
    input.parentNode.appendChild(err);
  },

  /** Clear error state on a field */
  clear(inputId) {
    const input = document.getElementById(inputId);
    if (!input) return;
    input.style.borderColor = '';
    input.style.boxShadow   = '';
    const existing = input.parentNode.querySelector('.field-error');
    if (existing) existing.remove();
  },

  /** Clear all error states */
  clearAll() {
    document.querySelectorAll('.field-error').forEach(e => e.remove());
    document.querySelectorAll('input, select').forEach(el => {
      el.style.borderColor = '';
      el.style.boxShadow   = '';
    });
  },

  /** Validate email format */
  isEmail(val) { return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val); },

  /** Validate Philippine phone */
  isPhone(val) { return /^(09|\+639)\d{9}$/.test(val.replace(/\s/g,'')); }
};

/* ── Auto-clear field errors on input ───────────────────── */
document.addEventListener('input', e => {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') {
    Validate.clear(e.target.id);
  }
});
