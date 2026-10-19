/* ==============================================================================
   AERORESERVE CLIENT JAVASCRIPT
   Interactive UX, API Integrations, Seat Selection & Database Modals
============================================================================== */

// Toast Notification System
function showToast(message, type = 'success') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    let icon = `
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
            <polyline points="22 4 12 14.01 9 11.01"></polyline>
        </svg>
    `;
    if (type === 'error') {
        icon = `
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="15" y1="9" x2="9" y2="15"></line>
                <line x1="9" y1="9" x2="15" y2="15"></line>
            </svg>
        `;
    }

    toast.innerHTML = `${icon} <span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Modal Toggle Helpers
function openModal(modalId) {
    const m = document.getElementById(modalId);
    if (m) {
        m.classList.add('active');
        if (window.lucide) lucide.createIcons();
    }
}

function closeModal(modalId) {
    const m = document.getElementById(modalId);
    if (m) m.classList.remove('active');
}

// Close modals when clicking backdrop
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-overlay')) {
        e.target.classList.remove('active');
    }
});

// Database Connection Modal & Switcher
async function openDbModal() {
    openModal('dbConfigModal');
    try {
        const res = await fetch('/api/db/status');
        const data = await res.json();
        document.getElementById('dbEngineDisplay').innerText = data.engine;
        document.getElementById('dbHostDisplay').innerText = data.host;
        document.getElementById('dbTablesDisplay').innerText = `${data.tables_count} Tables Active`;
        document.getElementById('cfgEngine').value = data.engine.toLowerCase();
    } catch (err) {
        console.error('Failed to fetch DB status', err);
    }
}

async function testAndApplyDbConfig(e) {
    if (e) e.preventDefault();
    const engine = document.getElementById('cfgEngine').value;
    const host = document.getElementById('cfgHost').value;
    const port = document.getElementById('cfgPort').value;
    const user = document.getElementById('cfgUser').value;
    const password = document.getElementById('cfgPassword').value;
    const database = document.getElementById('cfgDatabase').value;

    const btn = document.getElementById('btnSaveDb');
    btn.disabled = true;
    btn.innerText = 'Connecting & Verifying...';

    try {
        const res = await fetch('/api/db/configure', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ engine, host, port, user, password, database })
        });
        const result = await res.json();
        if (result.success) {
            showToast(result.message, 'success');
            setTimeout(() => window.location.reload(), 1000);
        } else {
            showToast(result.error, 'error');
        }
    } catch (err) {
        showToast('Connection failed: ' + err.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerText = 'Save & Connect';
    }
}

// Interactive Seat Selection Logic
let selectedSeat = null;
let basePrice = 0;

function initSeatSelection(flightBaseFare) {
    basePrice = parseFloat(flightBaseFare);
    const seatButtons = document.querySelectorAll('.seat:not(.booked), .seat-unit:not(.booked), .seat-btn:not(.booked)');
    seatButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            seatButtons.forEach(b => b.classList.remove('selected'));
            btn.classList.add('selected');
            selectedSeat = btn.dataset.seat;
            const seatClass = btn.dataset.class;

            const seatInput = document.getElementById('selectedSeatInput');
            if (seatInput) seatInput.value = selectedSeat;

            const seatBadge = document.getElementById('selectedSeatBadgeText');
            if (seatBadge) {
                seatBadge.innerText = `Seat ${selectedSeat} (${seatClass})`;
            }

            // Update Class select
            const classSelect = document.getElementById('travelClassSelect');
            if (classSelect) {
                classSelect.value = seatClass;
                updatePriceBreakdown(seatClass);
            }
        });
    });
}

function updatePriceBreakdown(travelClass) {
    let multiplier = 1.0;
    if (travelClass === 'BUSINESS') multiplier = 2.0;
    if (travelClass === 'FIRST') multiplier = 3.5;

    const subtotal = Math.round(basePrice * multiplier);
    const taxes = 350;
    const total = subtotal + taxes;

    const elSubtotal = document.getElementById('fareSubtotal');
    const elTotal = document.getElementById('fareTotal');
    if (elSubtotal) elSubtotal.innerText = `INR ${subtotal.toLocaleString()}`;
    if (elTotal) elTotal.innerText = `INR ${total.toLocaleString()}`;
}

// Complete Booking Flow Submission (Assessment 10)
async function submitBookingFlow(e) {
    e.preventDefault();
    const flightId = document.getElementById('bookingFlightId').value;
    const seatNumber = document.getElementById('selectedSeatInput').value;
    const travelClass = document.getElementById('travelClassSelect').value;
    const paymentMethod = document.getElementById('paymentMethodSelect').value;

    if (!seatNumber) {
        showToast('Please select a seat from the aircraft map to proceed.', 'warning');
        return;
    }

    const passenger = {
        first_name: document.getElementById('paxFirstName').value.trim(),
        last_name: document.getElementById('paxLastName').value.trim(),
        email: document.getElementById('paxEmail').value.trim(),
        phone: document.getElementById('paxPhone').value.trim(),
        passport_number: document.getElementById('paxPassport').value.trim(),
        date_of_birth: document.getElementById('paxDob').value,
        gender: document.getElementById('paxGender').value
    };

    const submitBtn = document.getElementById('btnConfirmBooking');
    submitBtn.disabled = true;
    submitBtn.innerHTML = `
        <svg class="animate-spin" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <circle cx="12" cy="12" r="10" stroke-width="4" stroke="currentColor" stroke-dasharray="32" stroke-linecap="round"></circle>
        </svg> Processing Transaction...
    `;

    try {
        const res = await fetch('/api/bookings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                flight_id: flightId,
                seat_number: seatNumber,
                travel_class: travelClass,
                payment_method: paymentMethod,
                passenger: passenger
            })
        });

        const data = await res.json();
        if (data.success) {
            showToast(`Booking Successful! PNR: ${data.pnr}`, 'success');
            setTimeout(() => {
                window.location.href = `/ticket/${data.pnr}`;
            }, 1200);
        } else {
            showToast(data.error || 'Booking transaction failed.', 'error');
            submitBtn.disabled = false;
            submitBtn.innerText = 'Confirm & Pay Now';
        }
    } catch (err) {
        showToast('Network error: ' + err.message, 'error');
        submitBtn.disabled = false;
        submitBtn.innerText = 'Confirm & Pay Now';
    }
}

// Assessment 8: Quick Passenger Insertion & Direct Verification
async function submitAssessment8Passenger(e) {
    e.preventDefault();
    const data = {
        first_name: document.getElementById('a8FirstName').value.trim(),
        last_name: document.getElementById('a8LastName').value.trim(),
        email: document.getElementById('a8Email').value.trim(),
        phone: document.getElementById('a8Phone').value.trim(),
        passport_number: document.getElementById('a8Passport').value.trim(),
        date_of_birth: document.getElementById('a8Dob').value || '1998-05-20',
        gender: document.getElementById('a8Gender').value || 'MALE'
    };

    const resBox = document.getElementById('a8VerificationResult');
    resBox.innerHTML = '<p class="text-muted">Inserting record into database...</p>';

    try {
        const res = await fetch('/api/passengers', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await res.json();
        if (result.success) {
            showToast(result.message, 'success');
            const p = result.data;
            resBox.innerHTML = `
                <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); padding: 1.25rem; border-radius: 8px; margin-top: 1rem;">
                    <div style="color: #34d399; font-weight: 700; margin-bottom: 0.5rem; display: flex; align-items: center; gap: 0.5rem;">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>
                        SUCCESSFULLY STORED & RETRIEVED FROM DATABASE (Assessment 8 Proof)
                    </div>
                    <table style="width: 100%; font-size: 0.85rem; border-collapse: collapse;">
                        <tr><td style="color: #94a3b8; padding: 4px 0;">Passenger ID (PK):</td><td style="font-family: monospace; font-weight: 700; color: #fff;">${p.passenger_id}</td></tr>
                        <tr><td style="color: #94a3b8; padding: 4px 0;">Full Name:</td><td style="font-weight: 600; color: #fff;">${p.first_name} ${p.last_name}</td></tr>
                        <tr><td style="color: #94a3b8; padding: 4px 0;">Email:</td><td style="color: #60a5fa;">${p.email}</td></tr>
                        <tr><td style="color: #94a3b8; padding: 4px 0;">Phone:</td><td>${p.phone}</td></tr>
                        <tr><td style="color: #94a3b8; padding: 4px 0;">Passport No:</td><td style="font-family: monospace;">${p.passport_number}</td></tr>
                        <tr><td style="color: #94a3b8; padding: 4px 0;">Created At:</td><td style="font-family: monospace; color: #a78bfa;">${p.created_at || 'Just now'}</td></tr>
                    </table>
                </div>
            `;
        } else {
            showToast(result.error, 'error');
            resBox.innerHTML = `<p style="color: #f87171;">Error: ${result.error}</p>`;
        }
    } catch (err) {
        showToast('Error: ' + err.message, 'error');
        resBox.innerHTML = `<p style="color: #f87171;">Error: ${err.message}</p>`;
    }
}

// Booking Cancellation (Assessment 9 & 10)
async function cancelBooking(pnr) {
    if (!confirm(`Are you sure you want to cancel booking PNR: ${pnr}? A full refund will be processed and the seat released.`)) {
        return;
    }

    try {
        const res = await fetch(`/api/bookings/${pnr}/cancel`, { method: 'POST' });
        const result = await res.json();
        if (result.success) {
            showToast(result.message, 'success');
            setTimeout(() => window.location.reload(), 1200);
        } else {
            showToast(result.error, 'error');
        }
    } catch (err) {
        showToast('Failed to cancel booking: ' + err.message, 'error');
    }
}

// Print Ticket helper
function printTicket() {
    window.print();
}
