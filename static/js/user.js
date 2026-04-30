/* ==========================================================
   BusBook — user.js  (fixed)
   Passenger-facing JS: booking history, profile helpers
   NOTE: book.html, seat-selection.html, transaction.html,
   paymongo.html each have their own inline JS that uses
   localStorage.currentBooking — this file must NOT override
   that pattern. user.js only handles profile & history.
   Requires: auth.js loaded first
   ========================================================== */

/* ── API helper ─────────────────────────────────────────── */
async function apiFetch(url, options = {}) {
  const res = await fetch(url, { headers: Auth.headers(), ...options });
  if (res.status === 401) { Auth.logout(); return null; }
  return res;
}

/* ── Profile init (profile.html) ────────────────────────── */
async function initProfile() {
  if (!Auth.requireLogin()) return;
  const user = Auth.getUser();
  if (user) {
    setEl('profileName',  `${user.first_name || ''} ${user.last_name || ''}`.trim() || user.email);
    setEl('profileEmail', user.email  || '—');
    setEl('profilePhone', user.phone  || '—');
    setEl('profileRole',  user.role   || 'passenger');
    setEl('avatarLetter', ((user.first_name || user.email || '?')[0]).toUpperCase());
  }
  await loadBookingHistory();
}

/* ── Booking history ────────────────────────────────────── */
// FIX: was /api/bookings/my — correct endpoint is /api/bookings/user/<id>
async function loadBookingHistory() {
  const listEl = document.getElementById('bookingList');
  if (!listEl) return;
  listEl.innerHTML = `<div class="empty-state"><div class="spinner"></div></div>`;

  const user = Auth.getUser();
  if (!user) return;

  try {
    const res = await apiFetch(`/api/bookings/user/${user.id}`);
    if (!res) return;
    const data = await res.json();
    renderBookingHistory(Array.isArray(data) ? data : (data.bookings || []), listEl);
  } catch {
    listEl.innerHTML = `<div class="empty-state"><p>Could not load bookings.</p></div>`;
  }
}

// FIX: was b.reference_code — correct field is b.booking_code; was b.price — correct is b.amount
function renderBookingHistory(bookings, container) {
  if (!bookings.length) {
    container.innerHTML = `
      <div class="empty-state">
        <span class="empty-icon">🎫</span>
        <p>No bookings yet. <a href="/book">Book your first ride!</a></p>
      </div>`;
    return;
  }
  container.innerHTML = bookings.map(b => `
    <div class="booking-card">
      <div class="booking-icon"><i class="fa-solid fa-bus"></i></div>
      <div class="booking-info">
        <div class="booking-route">${b.route || 'Unknown route'}</div>
        <div class="booking-meta">
          ${b.departure_time || b.time || '—'}
          &nbsp;·&nbsp; Seat ${b.seat_number || '—'}
          &nbsp;·&nbsp; ${b.travel_date || '—'}
          &nbsp;·&nbsp;
          <span class="badge badge-${b.status === 'confirmed' ? 'green' : b.status === 'cancelled' ? 'red' : 'yellow'}"
                style="font-size:11px;padding:1px 7px;">
            ${b.status || 'pending'}
          </span>
          ${b.discount_type ? `<span style="font-size:11px;font-weight:700;padding:1px 8px;border-radius:20px;background:rgba(16,185,129,.12);color:#059669;margin-left:4px;">${b.discount_type.toUpperCase()} 20% OFF</span>` : ''}
          ${b.trip_status && b.trip_status !== 'scheduled' ? `<span style="font-size:11px;font-weight:700;padding:1px 8px;border-radius:20px;margin-left:4px;background:rgba(244,162,97,.15);color:var(--brand-darker);">${{'boarding':'🚌 Boarding','departed':'🚀 Departed','arrived':'✅ Arrived','delayed':'⏰ Delayed','cancelled':'❌ Cancelled'}[b.trip_status]||b.trip_status}</span>` : ''}
        </div>
        <div style="font-size:11px;color:var(--text-3);margin-top:2px;">
          Ref: ${b.booking_code || '—'}
          ${b.payment_method && b.payment_method !== '—' ? ' · Paid via ' + b.payment_method : ''}
          ${b.passenger_type && b.passenger_type !== 'regular' ? ' · '+b.passenger_type.charAt(0).toUpperCase()+b.passenger_type.slice(1)+' passenger' : ''}
        </div>
      </div>
      <div style="text-align:right;flex-shrink:0;">
        <div style="font-weight:700;color:var(--brand-darker);">₱${Number(b.amount || b.fare || 0).toFixed(2)}</div>
        ${b.status === 'confirmed' && b.booking_code
          ? `<a href="/ticket?code=${b.booking_code}" class="btn btn-outline btn-sm" style="margin-top:6px;font-size:11px;">
               <i class="fa-solid fa-ticket"></i> View Ticket
             </a>`
          : ''}
        ${b.status === 'pending'
          ? `<button class="btn btn-outline btn-sm" style="margin-top:6px;font-size:11px;color:#dc2626;border-color:#dc2626;"
                     onclick="cancelBooking('${b.booking_code}')">
               <i class="fa-solid fa-xmark"></i> Cancel
             </button>`
          : ''}
      </div>
    </div>`).join('');
}

/* ── Cancel booking from profile ────────────────────────── */
async function cancelBooking(code) {
  if (!confirm(`Cancel booking ${code}? This cannot be undone.`)) return;
  try {
    const res = await apiFetch(`/api/bookings/cancel/${code}`, { method: 'POST' });
    if (!res) return;
    const data = await res.json();
    if (res.ok) { Toast.success('Booking cancelled.'); loadBookingHistory(); }
    else Toast.error(data.error || 'Could not cancel booking.');
  } catch { Toast.error('Network error.'); }
}

/* ── Profile edit ────────────────────────────────────────── */
async function saveProfile(formData) {
  try {
    const res = await apiFetch('/api/auth/profile', { method: 'PUT', body: JSON.stringify(formData) });
    if (!res) return;
    const data = await res.json();
    if (res.ok) {
      // Update stored user
      const user = Auth.getUser();
      if (user) Auth.saveSession(Auth.getToken(), { ...user, ...data.user });
      Toast.success('Profile updated!');
      initProfile();
    } else {
      Toast.error(data.error || 'Failed to update profile.');
    }
  } catch { Toast.error('Network error.'); }
}

/* ── Routes page ─────────────────────────────────────────── */
// routes.html has its own inline JS, but this is a fallback
async function initRoutes() {
  const container = document.getElementById('routeList');
  if (!container) return;
  try {
    const res = await fetch('/api/schedules/');
    const data = await res.json();
    const schedules = Array.isArray(data) ? data : (data.schedules || []);
    if (typeof filterRoutes === 'function') {
      window.allSchedules = schedules;
      filterRoutes();
    }
  } catch {
    if (container) container.innerHTML = `<div class="empty-state"><p>Could not load routes.</p></div>`;
  }
}

/* ── Utilities ──────────────────────────────────────────── */
function setEl(id, val) { const el = document.getElementById(id); if (el) el.textContent = val; }
function logout() { Auth.logout(); }
