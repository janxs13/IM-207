/* ==========================================================
   BusBook — user.js
   Passenger-facing JS: booking search, seat selection, profile
   Requires: auth.js loaded first
   ========================================================== */

/* ── API helper ─────────────────────────────────────────── */
async function apiFetch(url, options = {}) {
  const res = await fetch(url, {
    headers: Auth.headers(),
    ...options
  });

  if (res.status === 401) {
    Auth.logout();
    return null;
  }

  return res;
}

/* ── Schedule / Booking search (book.html) ──────────────── */
async function searchSchedules() {
  const origin      = document.getElementById('origin')?.value?.trim();
  const destination = document.getElementById('destination')?.value?.trim();
  const date        = document.getElementById('travel_date')?.value;
  const resultsEl   = document.getElementById('searchResults');

  if (!origin || !destination || !date) {
    Toast.warning('Please fill in all fields.');
    return;
  }

  if (!Auth.requireLogin()) return;

  if (resultsEl) {
    resultsEl.innerHTML = `<div class="text-center mt-16"><div class="spinner"></div></div>`;
    resultsEl.style.display = 'block';
  }

  try {
    const params = new URLSearchParams({ origin, destination, date });
    const res = await apiFetch(`/api/schedules/search?${params}`);
    if (!res) return;

    const data = await res.json();
    renderScheduleResults(data.schedules || [], resultsEl);
  } catch (err) {
    if (resultsEl) resultsEl.innerHTML = `<div class="alert alert-error">Failed to load schedules. Please try again.</div>`;
  }
}

function renderScheduleResults(schedules, container) {
  if (!container) return;

  if (!schedules.length) {
    container.innerHTML = `<div class="empty-state"><span class="empty-icon">🔍</span><p>No schedules found for this route and date.</p></div>`;
    return;
  }

  container.innerHTML = schedules.map(s => `
    <div class="route-card" onclick="selectSchedule(${s.id}, '${s.route}', '${s.departure_time}', ${s.price})">
      <div class="route-from-to">
        <div>
          <div class="route-city">${s.route.split(' - ')[0] || s.route}</div>
          <div class="route-time">${s.departure_time}</div>
        </div>
        <div class="route-arrow"><i class="fa-solid fa-arrow-right"></i></div>
        <div>
          <div class="route-city">${s.route.split(' - ')[1] || '—'}</div>
          <div class="route-time">${s.arrival_time || 'TBA'}</div>
        </div>
      </div>
      <div>
        <span class="badge badge-${s.available_seats > 5 ? 'green' : s.available_seats > 0 ? 'yellow' : 'red'}">
          ${s.available_seats} seats left
        </span>
      </div>
      <div class="route-price">₱${Number(s.price).toFixed(2)}</div>
      <button class="btn btn-primary btn-sm">Select</button>
    </div>
  `).join('');
}

function selectSchedule(id, route, time, price) {
  sessionStorage.setItem('selectedSchedule', JSON.stringify({ id, route, time, price }));
  window.location.href = '/seat-selection';
}

/* ── Seat selection (seat-selection.html) ───────────────── */
let selectedSeat = null;
let scheduleData = null;

async function initSeatSelection() {
  const info = JSON.parse(sessionStorage.getItem('selectedSchedule') || 'null');
  if (!info) { window.location.href = '/book'; return; }
  scheduleData = info;

  const summaryEl = document.getElementById('tripSummary');
  if (summaryEl) {
    const parts = info.route.split(' - ');
    summaryEl.innerHTML = `
      <div style="font-weight:700;font-size:15px;">${parts[0]} → ${parts[1] || '—'}</div>
      <div style="font-size:13px;color:var(--text-3);margin-top:4px;">${info.time} &nbsp;|&nbsp; ₱${Number(info.price).toFixed(2)}</div>
    `;
  }

  await loadSeats(info.id);
}

async function loadSeats(scheduleId) {
  try {
    const res = await apiFetch(`/api/schedules/${scheduleId}/seats`);
    if (!res) return;
    const data = await res.json();
    renderSeatMap(data.seats || []);
  } catch (err) {
    Toast.error('Could not load seat map.');
  }
}

function renderSeatMap(seats) {
  const grid = document.getElementById('seatGrid');
  if (!grid) return;

  grid.innerHTML = seats.map(seat => {
    const cls = seat.status === 'available' ? 'seat-available' :
                seat.status === 'held'      ? 'seat-held' : 'seat-taken';
    const clickable = seat.status === 'available' ? `onclick="pickSeat('${seat.seat_number}', this)"` : '';
    return `<div class="seat ${cls}" ${clickable} title="Seat ${seat.seat_number}">${seat.seat_number}</div>`;
  }).join('');
}

function pickSeat(seatNum, el) {
  document.querySelectorAll('.seat-selected').forEach(s => {
    s.classList.remove('seat-selected');
    s.classList.add('seat-available');
  });
  el.classList.remove('seat-available');
  el.classList.add('seat-selected');
  selectedSeat = seatNum;

  const display = document.getElementById('selectedSeatDisplay');
  const confirmBtn = document.getElementById('confirmSeatBtn');
  if (display) display.textContent = seatNum;
  if (confirmBtn) confirmBtn.disabled = false;
}

async function confirmSeat() {
  if (!selectedSeat || !scheduleData) return;
  if (!Auth.requireLogin()) return;

  try {
    const res = await apiFetch('/api/bookings/', {
      method: 'POST',
      body: JSON.stringify({
        schedule_id: scheduleData.id,
        seat_number: selectedSeat
      })
    });

    if (!res) return;
    const data = await res.json();

    if (res.ok && data.booking_id) {
      sessionStorage.setItem('bookingId', data.booking_id);
      sessionStorage.setItem('bookingRef', data.reference_code || '');
      window.location.href = '/transaction';
    } else {
      Toast.error(data.message || 'Booking failed. Please try again.');
    }
  } catch (err) {
    Toast.error('Network error. Please try again.');
  }
}

/* ── Transaction / Payment (transaction.html) ───────────── */
async function initTransaction() {
  const bookingId = sessionStorage.getItem('bookingId');
  if (!bookingId) { window.location.href = '/book'; return; }

  try {
    const res = await apiFetch(`/api/bookings/${bookingId}`);
    if (!res) return;
    const data = await res.json();
    renderTransactionSummary(data);
  } catch (err) {
    Toast.error('Failed to load booking details.');
  }
}

function renderTransactionSummary(booking) {
  const el = document.getElementById('transactionSummary');
  if (!el || !booking) return;
  el.innerHTML = `
    <div class="flex justify-between mb-16">
      <span class="text-muted">Route</span>
      <span class="fw-600">${booking.route || '—'}</span>
    </div>
    <div class="flex justify-between mb-16">
      <span class="text-muted">Seat</span>
      <span class="fw-600">${booking.seat_number || '—'}</span>
    </div>
    <div class="flex justify-between mb-16">
      <span class="text-muted">Departure</span>
      <span class="fw-600">${booking.departure_time || '—'}</span>
    </div>
    <div class="flex justify-between" style="font-size:18px;font-weight:800;color:var(--brand-darker)">
      <span>Total</span>
      <span>₱${Number(booking.price || 0).toFixed(2)}</span>
    </div>
  `;
}

async function payWith(method) {
  const bookingId = sessionStorage.getItem('bookingId');
  if (!bookingId) return;

  try {
    const res = await apiFetch('/api/payments/', {
      method: 'POST',
      body: JSON.stringify({ booking_id: bookingId, payment_method: method })
    });

    if (!res) return;
    const data = await res.json();

    if (res.ok) {
      const routes = { gcash: '/gcash', paymaya: '/paymaya', paypal: '/paypal' };
      window.location.href = routes[method] || '/ticket';
    } else {
      Toast.error(data.message || 'Payment failed.');
    }
  } catch (err) {
    Toast.error('Network error. Please try again.');
  }
}

/* ── Profile & booking history (profile.html) ───────────── */
async function initProfile() {
  if (!Auth.requireLogin()) return;

  const user = Auth.getUser();
  if (user) {
    setEl('profileName',  user.username || user.email);
    setEl('profileEmail', user.email || '—');
    setEl('profilePhone', user.phone || '—');
    setEl('profileRole',  user.role || 'passenger');
    setEl('avatarLetter', (user.username || user.email || '?')[0].toUpperCase());
  }

  await loadBookingHistory();
}

async function loadBookingHistory() {
  const listEl = document.getElementById('bookingList');
  if (!listEl) return;

  listEl.innerHTML = `<div class="text-center mt-16"><div class="spinner"></div></div>`;

  try {
    const res = await apiFetch('/api/bookings/my');
    if (!res) return;
    const data = await res.json();
    renderBookingHistory(data.bookings || [], listEl);
  } catch {
    listEl.innerHTML = `<div class="alert alert-error">Could not load bookings.</div>`;
  }
}

function renderBookingHistory(bookings, container) {
  if (!bookings.length) {
    container.innerHTML = `<div class="empty-state"><span class="empty-icon">🎫</span><p>No bookings yet. <a href="/book">Book your first ride!</a></p></div>`;
    return;
  }

  container.innerHTML = bookings.map(b => `
    <div class="booking-card">
      <div class="booking-icon"><i class="fa-solid fa-bus"></i></div>
      <div class="booking-info">
        <div class="booking-route">${b.route || 'Unknown route'}</div>
        <div class="booking-meta">
          ${b.departure_time || '—'} &nbsp;·&nbsp; Seat ${b.seat_number || '—'} &nbsp;·&nbsp;
          <span class="badge badge-${b.status === 'confirmed' ? 'green' : b.status === 'cancelled' ? 'red' : 'yellow'}" style="font-size:11px;padding:1px 7px;">
            ${b.status || 'pending'}
          </span>
        </div>
      </div>
      <div style="text-align:right;flex-shrink:0;">
        <div style="font-weight:700;color:var(--brand-darker);">₱${Number(b.price || 0).toFixed(2)}</div>
        <a href="/ticket?ref=${b.reference_code}" class="text-xs" style="color:var(--blue);">View ticket</a>
      </div>
    </div>
  `).join('');
}

/* ── Routes listing (routes.html) ───────────────────────── */
let allSchedules = [];

async function initRoutes() {
  const container = document.getElementById('routeList');
  if (!container) return;

  container.innerHTML = `<div class="text-center mt-16"><div class="spinner"></div></div>`;

  try {
    const res = await fetch('/api/schedules/');
    const data = await res.json();
    allSchedules = data.schedules || [];
    filterRoutes();
  } catch {
    container.innerHTML = `<div class="alert alert-error">Could not load routes.</div>`;
  }
}

function filterRoutes() {
  const q = (document.getElementById('searchInput')?.value || '').toLowerCase();
  const filtered = allSchedules.filter(s => s.route.toLowerCase().includes(q));
  renderRoutes(filtered);
}

function renderRoutes(list) {
  const container = document.getElementById('routeList');
  if (!container) return;

  if (!list.length) {
    container.innerHTML = `<div class="empty-state"><span class="empty-icon">🗺️</span><p>No routes found.</p></div>`;
    return;
  }

  container.innerHTML = list.map(s => {
    const parts = s.route.split(' - ');
    return `
      <div class="route-card" onclick="window.location.href='/book'">
        <div class="route-from-to">
          <div>
            <div class="route-city">${parts[0] || s.route}</div>
            <div class="route-time">${s.departure_time || '—'}</div>
          </div>
          <div class="route-arrow"><i class="fa-solid fa-arrow-right"></i></div>
          <div>
            <div class="route-city">${parts[1] || '—'}</div>
            <div class="route-time">${s.arrival_time || 'TBA'}</div>
          </div>
        </div>
        <div>
          <span class="badge badge-${s.available_seats > 5 ? 'green' : s.available_seats > 0 ? 'yellow' : 'red'}">
            ${s.available_seats} seats
          </span>
        </div>
        <div class="route-price">₱${Number(s.price).toFixed(2)}</div>
        <button class="btn btn-primary btn-sm">Book Now</button>
      </div>
    `;
  }).join('');
}

/* ── Utilities ──────────────────────────────────────────── */
function setEl(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

function logout() {
  Auth.logout();
}
