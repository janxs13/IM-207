/* ==========================================================
   BusBook — admin.js  (fixed)
   Admin panel JS: dashboard stats, manage pages
   Requires: auth.js loaded first
   ========================================================== */

/* ── Guard ──────────────────────────────────────────────── */
function requireAdmin() { return Auth.requireAdmin(); }
function renderAdminUser() { Auth.renderSidebarUser('sidebarUserName', 'sidebarAvatar'); }

/* ── API helper ─────────────────────────────────────────── */
async function adminFetch(url, options = {}) {
  const res = await fetch(url, { headers: Auth.headers(), ...options });
  if (res.status === 401) { Auth.logout(); return null; }
  return res;
}

/* ── Dashboard stats ────────────────────────────────────── */
// FIX: was /api/admin/stats — correct endpoint is /api/admin/dashboard
async function loadDashboardStats() {
  try {
    const res = await adminFetch('/api/admin/dashboard');
    if (!res) return;
    const data = await res.json();
    setEl('statUsers',    data.total_users    ?? '—');
    setEl('statBookings', data.total_bookings ?? '—');
    setEl('statRevenue',  data.total_revenue  != null
      ? '₱' + Number(data.total_revenue).toLocaleString('en-PH', {minimumFractionDigits:2})
      : '—');
    setEl('statBuses',    data.total_buses    ?? '—');
    setEl('statSchedules', data.total_schedules ?? '—');
    setEl('statConfirmed', data.confirmed     ?? '—');
    setEl('statCancelled', data.cancelled     ?? '—');
    setEl('statPending',   data.pending       ?? '—');
  } catch (err) {
    console.error('Stats load failed:', err);
  }
}

async function loadRecentBookings() {
  const container = document.getElementById('recentBookings');
  if (!container) return;
  try {
    const res = await adminFetch('/api/admin/bookings/recent');
    if (!res) return;
    const data = await res.json();
    renderRecentBookings(data.bookings || [], container);
  } catch {
    container.innerHTML = `<div class="alert alert-error" style="margin:16px;">Failed to load bookings.</div>`;
  }
}

function renderRecentBookings(bookings, container) {
  if (!bookings.length) {
    container.innerHTML = `<div class="empty-state"><span class="empty-icon">📋</span><p>No recent bookings.</p></div>`;
    return;
  }
  container.innerHTML = `
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Ref</th><th>Passenger</th><th>Route</th>
            <th>Seat</th><th>Amount</th><th>Status</th>
          </tr>
        </thead>
        <tbody>
          ${bookings.map(b => `
            <tr>
              <td><code style="font-size:12px;background:var(--surface2);padding:2px 6px;border-radius:4px;">
                ${b.booking_code || '—'}
              </code></td>
              <td>${b.passenger || b.email || '—'}</td>
              <td>${b.route || '—'}</td>
              <td>${b.seat_number || '—'}</td>
              <td style="font-weight:600;">₱${Number(b.amount || 0).toFixed(2)}</td>
              <td><span class="badge badge-${b.status === 'confirmed' ? 'green' : b.status === 'cancelled' ? 'red' : 'yellow'}">${b.status}</span></td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>`;
}

/* ── Users ──────────────────────────────────────────────── */
async function loadUsers() {
  const container = document.getElementById('userTableBody');
  if (!container) return;
  try {
    const res = await adminFetch('/api/admin/users');
    if (!res) return;
    const data = await res.json();
    renderUserTable(data.users || [], container);
  } catch { Toast.error('Failed to load users.'); }
}

function renderUserTable(users, tbody) {
  if (!users.length) {
    tbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted" style="padding:32px;">No users found.</td></tr>`;
    return;
  }
  tbody.innerHTML = users.map(u => `
    <tr>
      <td>
        <div style="display:flex;align-items:center;gap:10px;">
          <div style="width:32px;height:32px;background:var(--brand-light);border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;color:var(--brand-darker);font-size:13px;">
            ${(u.username || u.email || 'U')[0].toUpperCase()}
          </div>
          <span class="fw-600">${u.username || '—'}</span>
        </div>
      </td>
      <td>${u.email || '—'}</td>
      <td>${u.phone || '—'}</td>
      <td><span class="badge badge-${u.role === 'admin' ? 'blue' : 'brand'}">${u.role}</span></td>
      <td>${u.booking_count ?? 0}</td>
      <td>
        <button class="btn btn-danger btn-sm" onclick="deleteUser(${u.id})">
          <i class="fa-solid fa-trash"></i>
        </button>
      </td>
    </tr>`).join('');
}

async function deleteUser(userId) {
  if (!confirm('Delete this user? This cannot be undone.')) return;
  try {
    const res = await adminFetch(`/api/admin/users/${userId}`, { method: 'DELETE' });
    if (!res) return;
    if (res.ok) { Toast.success('User deleted.'); loadUsers(); }
    else { const d = await res.json(); Toast.error(d.error || 'Could not delete user.'); }
  } catch { Toast.error('Network error.'); }
}

/* ── Buses ──────────────────────────────────────────────── */
async function loadBuses() {
  const container = document.getElementById('busTableBody');
  if (!container) return;
  try {
    const res = await adminFetch('/api/admin/buses');
    if (!res) return;
    const data = await res.json();
    renderBusTable(data.buses || [], container);
  } catch { Toast.error('Failed to load buses.'); }
}

// FIX: was b.bus_number / b.bus_type — correct fields are b.name/b.bus_name / b.seat_layout
function renderBusTable(buses, tbody) {
  if (!buses.length) {
    tbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted" style="padding:32px;">No buses found.</td></tr>`;
    return;
  }
  tbody.innerHTML = buses.map(b => `
    <tr>
      <td class="fw-600">${b.bus_name || b.name || '—'}</td>
      <td>${b.plate_number || '—'}</td>
      <td>${b.total_seats || '—'}</td>
      <td>${b.seat_layout || '—'}</td>
      <td><span class="badge badge-${b.is_active !== false ? 'green' : 'red'}">${b.is_active !== false ? 'Active' : 'Inactive'}</span></td>
      <td style="display:flex;gap:8px;">
        <button class="btn btn-outline btn-sm" onclick="editBus(${b.id})"><i class="fa-solid fa-pen"></i></button>
        <button class="btn btn-danger btn-sm" onclick="deleteBus(${b.id})"><i class="fa-solid fa-trash"></i></button>
      </td>
    </tr>`).join('');
}

async function addBus(formData) {
  try {
    const res = await adminFetch('/api/admin/buses', { method: 'POST', body: JSON.stringify(formData) });
    if (!res) return;
    const data = await res.json();
    if (res.ok) { Toast.success('Bus added!'); closeModal('busModal'); loadBuses(); }
    else Toast.error(data.error || 'Failed to add bus.');
  } catch { Toast.error('Network error.'); }
}

async function deleteBus(busId) {
  if (!confirm('Delete this bus?')) return;
  try {
    const res = await adminFetch(`/api/admin/buses/${busId}`, { method: 'DELETE' });
    if (!res) return;
    if (res.ok) { Toast.success('Bus deleted.'); loadBuses(); }
    else { const d = await res.json(); Toast.error(d.error || 'Could not delete bus.'); }
  } catch { Toast.error('Network error.'); }
}

/* ── Schedules ──────────────────────────────────────────── */
async function loadSchedules() {
  const container = document.getElementById('scheduleTableBody');
  if (!container) return;
  try {
    const res = await adminFetch('/api/schedules/');
    if (!res) return;
    const data = await res.json();
    renderScheduleTable(data.schedules || [], container);
  } catch { Toast.error('Failed to load schedules.'); }
}

// FIX: was s.price / s.bus_number / s.available_seats — correct fields below
function renderScheduleTable(schedules, tbody) {
  if (!schedules.length) {
    tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted" style="padding:32px;">No schedules found.</td></tr>`;
    return;
  }
  tbody.innerHTML = schedules.map(s => `
    <tr>
      <td class="fw-600">${s.route || '—'}</td>
      <td>${s.bus_name || '—'}</td>
      <td>${s.departure_time || '—'}</td>
      <td>${s.arrival_time || '—'}</td>
      <td style="font-weight:600;color:var(--brand-darker);">₱${Number(s.fare || s.price || 0).toFixed(2)}</td>
      <td><span class="badge badge-${(s.seats_available ?? s.available_seats ?? 0) > 0 ? 'green' : 'red'}">
        ${s.seats_available ?? s.available_seats ?? 0} seats
      </span></td>
      <td style="display:flex;gap:8px;">
        <button class="btn btn-outline btn-sm" onclick="editSchedule(${s.id})"><i class="fa-solid fa-pen"></i></button>
        <button class="btn btn-danger btn-sm" onclick="deleteSchedule(${s.id})"><i class="fa-solid fa-trash"></i></button>
      </td>
    </tr>`).join('');
}

async function deleteSchedule(id) {
  if (!confirm('Delete this schedule?')) return;
  try {
    const res = await adminFetch(`/api/schedules/${id}`, { method: 'DELETE' });
    if (!res) return;
    if (res.ok) { Toast.success('Schedule deleted.'); loadSchedules(); }
    else { const d = await res.json(); Toast.error(d.error || 'Could not delete.'); }
  } catch { Toast.error('Network error.'); }
}

/* ── Verify ticket ──────────────────────────────────────── */
async function verifyTicket() {
  const code = (document.getElementById('ticketCode')?.value || '').trim().toUpperCase();
  if (!code) { Toast.warning('Enter a ticket code or scan QR.'); return; }
  const resultEl = document.getElementById('verifyResult');
  if (resultEl) resultEl.style.display = 'none';
  try {
    const res = await adminFetch(`/api/verify/${code}`);
    if (!res) return;
    const data = await res.json();
    renderVerifyResult(data, resultEl);
  } catch { Toast.error('Verification failed.'); }
}

function renderVerifyResult(data, container) {
  if (!container) return;
  container.style.display = 'block';
  const valid = data.valid || data.status === 'confirmed';
  container.innerHTML = `
    <div class="verify-result">
      <div class="verify-result-header ${valid ? 'valid' : 'invalid'}">
        <div class="verify-status-icon ${valid ? 'valid' : 'invalid'}">
          <i class="fa-solid fa-${valid ? 'check' : 'xmark'}"></i>
        </div>
        <div>
          <div style="font-weight:700;font-size:16px;color:${valid ? '#065f46' : '#991b1b'}">
            ${valid ? 'Valid Ticket' : 'Invalid Ticket'}
          </div>
          <div style="font-size:13px;color:${valid ? '#065f46' : '#991b1b'}">
            ${data.message || (valid ? 'Ticket is authentic.' : 'Not found or already used.')}
          </div>
        </div>
      </div>
      ${valid && data.booking ? `
        <div style="padding:20px 24px;">
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;font-size:14px;">
            <div><span style="color:var(--text-3);">Passenger</span><br><strong>${data.booking.passenger || data.booking.passenger_name || '—'}</strong></div>
            <div><span style="color:var(--text-3);">Route</span><br><strong>${data.booking.route || '—'}</strong></div>
            <div><span style="color:var(--text-3);">Seat</span><br><strong>${data.booking.seat_number || '—'}</strong></div>
            <div><span style="color:var(--text-3);">Departure</span><br><strong>${data.booking.departure_time || data.booking.departure || '—'}</strong></div>
            <div><span style="color:var(--text-3);">Travel Date</span><br><strong>${data.booking.travel_date || '—'}</strong></div>
            <div><span style="color:var(--text-3);">Amount</span><br><strong>₱${Number(data.booking.amount || 0).toFixed(2)}</strong></div>
          </div>
        </div>` : ''}
    </div>`;
}

/* ── Modal helpers ──────────────────────────────────────── */
function openModal(id)  { const el = document.getElementById(id); if (el) el.classList.add('open'); }
function closeModal(id) { const el = document.getElementById(id); if (el) el.classList.remove('open'); }

/* ── Utilities ──────────────────────────────────────────── */
function setEl(id, val) { const el = document.getElementById(id); if (el) el.textContent = val; }
function logout() { Auth.logout(); }

document.addEventListener('click', (e) => {
  if (e.target.classList.contains('admin-modal')) e.target.classList.remove('open');
});
