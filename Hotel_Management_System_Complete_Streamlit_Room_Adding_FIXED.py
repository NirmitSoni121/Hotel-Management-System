import streamlit as st
from datetime import date, timedelta, datetime
import pandas as pd
import uuid

st.set_page_config(page_title="Hotel Management System", page_icon="🏨", layout="wide")

# =========================
# SESSION STATE / DATA
# =========================
if "rooms" not in st.session_state:
    st.session_state.rooms = {
        101: {"type": "Deluxe", "rate": 4000, "status": "Available", "readiness": "Ready"},
        102: {"type": "Deluxe", "rate": 4000, "status": "Available", "readiness": "Ready"},
        201: {"type": "Premium", "rate": 3000, "status": "Available", "readiness": "Ready"},
        202: {"type": "Premium", "rate": 3000, "status": "Available", "readiness": "Ready"},
        301: {"type": "Standard", "rate": 2000, "status": "Available", "readiness": "Ready"},
        302: {"type": "Standard", "rate": 2000, "status": "Available", "readiness": "Ready"},
        401: {"type": "Economy", "rate": 1000, "status": "Available", "readiness": "Ready"},
        402: {"type": "Economy", "rate": 1000, "status": "Available", "readiness": "Ready"},
    }

for key, default in {
    "bookings": [],
    "housekeeping": [],
    "payments": [],
    "next_booking": 1001,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

FOOD = {
    "Breakfast": 90,
    "Lunch": 110,
    "Dinner": 150,
    "Drink": 50,
    "Dessert": 100,
}
SERVICES = {
    "Laundry": 200,
    "Room Cleaning": 150,
    "Spa": 800,
    "Airport Pickup": 1000,
    "Extra Bed": 500,
}
HOUSEKEEPING_STAFF = ["Amit", "Rahul", "Priya", "Neha"]
BOOKING_STATUSES = ["Confirmed", "Checked-in", "Checked-out", "Cancelled"]

# =========================
# HELPERS
# =========================
def room_available(room_no, check_in, check_out, ignore_booking_id=None):
    room = st.session_state.rooms[room_no]
    if room["status"] == "Maintenance" or room["readiness"] != "Ready":
        return False

    for b in st.session_state.bookings:
        if b["booking_id"] == ignore_booking_id:
            continue
        if b["room"] != room_no or b["status"] == "Cancelled":
            continue
        existing_in = date.fromisoformat(b["check_in"])
        existing_out = date.fromisoformat(b["check_out"])
        if check_in < existing_out and check_out > existing_in:
            return False
    return True

def nights_between(check_in, check_out):
    n = (check_out - check_in).days
    return max(1, n)

def calculate_total(rate, nights, discount_percent):
    room_total = rate * nights
    discount = room_total * discount_percent / 100
    taxable = room_total - discount
    tax = taxable * 0.05
    total = taxable + tax
    return room_total, discount, tax, total

def active_bookings():
    return [b for b in st.session_state.bookings if b["status"] != "Cancelled"]

def find_booking(booking_id):
    for b in st.session_state.bookings:
        if b["booking_id"] == booking_id:
            return b
    return None

def room_df():
    rows = []
    for room_no, r in st.session_state.rooms.items():
        rows.append({
            "Room": room_no,
            "Category": r["type"],
            "Price/Night": f"₹{r['rate']:,}",
            "Occupancy": r["status"],
            "Readiness": r["readiness"]
        })
    return pd.DataFrame(rows)

def set_housekeeping(room_no, task, staff, status):
    existing = next((x for x in st.session_state.housekeeping if x["room"] == room_no), None)
    if existing:
        existing.update({"task": task, "staff": staff, "status": status})
    else:
        st.session_state.housekeeping.append({
            "room": room_no, "task": task, "staff": staff, "status": status
        })

# =========================
# HEADER
# =========================
st.title("🏨 Hotel Management System")
st.caption("Guest • Front Desk • Room Management • Housekeeping • Billing • Payments")

with st.sidebar:
    st.header("📋 Modules")
    page = st.radio(
        "Navigate",
        [
            "📊 Dashboard",
            "🔎 Browse Rooms",
            "🏨 Bookings",
            "🛏️ Room Management",
            "🧹 Housekeeping",
            "💰 Billing & Payments",
            "📋 Records"
        ]
    )

# =========================
# DASHBOARD
# =========================
if page == "📊 Dashboard":
    st.subheader("📊 Real-Time Hotel Dashboard")

    total_rooms = len(st.session_state.rooms)
    occupied = sum(1 for r in st.session_state.rooms.values() if r["status"] == "Occupied")
    maintenance = sum(1 for r in st.session_state.rooms.values() if r["status"] == "Maintenance")
    ready = sum(1 for r in st.session_state.rooms.values() if r["readiness"] == "Ready")
    confirmed = sum(1 for b in st.session_state.bookings if b["status"] == "Confirmed")
    pending_payments = sum(1 for p in st.session_state.payments if p["status"] == "Pending")

    c = st.columns(6)
    c[0].metric("Total Rooms", total_rooms)
    c[1].metric("Occupied", occupied)
    c[2].metric("Available", total_rooms - occupied - maintenance)
    c[3].metric("Maintenance", maintenance)
    c[4].metric("Ready Rooms", ready)
    c[5].metric("Pending Payments", pending_payments)

    st.divider()
    st.subheader("🛏️ Live Room Status")
    st.dataframe(room_df(), use_container_width=True, hide_index=True)

    st.subheader("📅 Current Booking Status")
    if active_bookings():
        data = [{
            "Booking ID": b["booking_id"],
            "Guest": b["guest"],
            "Room": b["room"],
            "Check-in": b["check_in"],
            "Check-out": b["check_out"],
            "Status": b["status"],
            "Payment": b["payment_status"]
        } for b in active_bookings()]
        st.dataframe(data, use_container_width=True, hide_index=True)
    else:
        st.info("No active bookings.")

# =========================
# BROWSE ROOMS
# =========================
elif page == "🔎 Browse Rooms":
    st.subheader("🔎 Browse Rooms by Category, Price & Availability")

    c1, c2, c3 = st.columns(3)
    categories = ["All"] + sorted({r["type"] for r in st.session_state.rooms.values()})
    category = c1.selectbox("Room Category", categories)
    max_price = c2.number_input("Maximum Price / Night", min_value=500, value=5000, step=500)
    check_in = c3.date_input("Check-in", date.today(), key="browse_in")
    check_out = st.date_input("Check-out", check_in + timedelta(days=1), key="browse_out")

    if check_out <= check_in:
        st.error("Checkout date must be after check-in.")
    else:
        results = []
        for room_no, r in st.session_state.rooms.items():
            if category != "All" and r["type"] != category:
                continue
            if r["rate"] > max_price:
                continue
            results.append({
                "Room": room_no,
                "Category": r["type"],
                "Price/Night": f"₹{r['rate']:,}",
                "Available for Dates": "Yes" if room_available(room_no, check_in, check_out) else "No",
                "Readiness": r["readiness"]
            })
        st.dataframe(results, use_container_width=True, hide_index=True)

# =========================
# BOOKINGS
# =========================
elif page == "🏨 Bookings":
    st.subheader("🏨 Booking Management")

    tabs = st.tabs(["➕ New Booking", "✏️ Modify", "❌ Cancel", "🔄 Check-in / Check-out"])

    with tabs[0]:
        st.markdown("### Guest Details")
        a, b = st.columns(2)
        guest = a.text_input("Full Name", key="new_guest")
        phone = a.text_input("Phone", key="new_phone")
        email = b.text_input("Email", key="new_email")
        guests = b.number_input("Number of Guests", 1, 20, 1, key="new_guests")

        c1, c2, c3 = st.columns(3)
        cin = c1.date_input("Check-in", date.today(), key="new_in")
        cout = c2.date_input("Check-out", date.today() + timedelta(days=1), key="new_out")
        discount = c3.number_input("Discount %", 0.0, 50.0, 0.0, step=1.0, key="new_discount")

        available_rooms = [
            r for r in st.session_state.rooms
            if room_available(r, cin, cout)
        ]
        if available_rooms:
            room = st.selectbox("Available Room", available_rooms, key="new_room")
            rinfo = st.session_state.rooms[room]
            n = nights_between(cin, cout)
            room_total, disc, tax, grand = calculate_total(rinfo["rate"], n, discount)

            p1, p2, p3, p4 = st.columns(4)
            p1.metric("Nights", n)
            p2.metric("Room Total", f"₹{room_total:,.0f}")
            p3.metric("Discount", f"₹{disc:,.0f}")
            p4.metric("Final Total", f"₹{grand:,.0f}")

            if st.button("✅ Confirm Booking", use_container_width=True):
                if not guest or not phone:
                    st.error("Guest name and phone are required.")
                elif cout <= cin:
                    st.error("Checkout date must be after check-in.")
                else:
                    booking_id = f"HMS-{st.session_state.next_booking}"
                    st.session_state.next_booking += 1
                    st.session_state.bookings.append({
                        "booking_id": booking_id,
                        "guest": guest,
                        "phone": phone,
                        "email": email,
                        "guests": guests,
                        "room": room,
                        "check_in": cin.isoformat(),
                        "check_out": cout.isoformat(),
                        "nights": n,
                        "discount": discount,
                        "room_total": room_total,
                        "tax": tax,
                        "total": grand,
                        "status": "Confirmed",
                        "payment_status": "Pending"
                    })
                    st.success(f"Booking {booking_id} created successfully.")
        else:
            st.warning("No room is available for the selected dates.")

    with tabs[1]:
        active = active_bookings()
        if not active:
            st.info("No booking available to modify.")
        else:
            ids = [b["booking_id"] for b in active]
            selected = st.selectbox("Select Booking", ids, key="modify_id")
            booking = find_booking(selected)
            st.write(f"**Guest:** {booking['guest']} | **Current Room:** {booking['room']}")

            new_in = st.date_input("New Check-in", date.fromisoformat(booking["check_in"]), key="mod_in")
            new_out = st.date_input("New Check-out", date.fromisoformat(booking["check_out"]), key="mod_out")
            new_rooms = [
                r for r in st.session_state.rooms
                if room_available(r, new_in, new_out, ignore_booking_id=booking["booking_id"])
            ]
            if booking["room"] not in new_rooms:
                new_rooms.append(booking["room"])

            new_room = st.selectbox("New Room", sorted(new_rooms), key="mod_room")
            new_discount = st.number_input("New Discount %", 0.0, 50.0, float(booking["discount"]), step=1.0)

            if st.button("💾 Save Changes", use_container_width=True):
                if new_out <= new_in:
                    st.error("Checkout date must be after check-in.")
                else:
                    n = nights_between(new_in, new_out)
                    rate = st.session_state.rooms[new_room]["rate"]
                    room_total, disc, tax, grand = calculate_total(rate, n, new_discount)
                    booking.update({
                        "room": new_room,
                        "check_in": new_in.isoformat(),
                        "check_out": new_out.isoformat(),
                        "nights": n,
                        "discount": new_discount,
                        "room_total": room_total,
                        "tax": tax,
                        "total": grand
                    })
                    st.success("Booking modified successfully.")

    with tabs[2]:
        active = active_bookings()
        if active:
            ids = [b["booking_id"] for b in active]
            cancel_id = st.selectbox("Booking to cancel", ids, key="cancel_id")
            if st.button("❌ Cancel Booking", use_container_width=True):
                booking = find_booking(cancel_id)
                booking["status"] = "Cancelled"
                st.success(f"Booking {cancel_id} cancelled.")
        else:
            st.info("No active booking to cancel.")

    with tabs[3]:
        active = active_bookings()
        if active:
            selected = st.selectbox("Booking", [b["booking_id"] for b in active], key="status_id")
            booking = find_booking(selected)
            new_status = st.selectbox("Update Status", ["Confirmed", "Checked-in", "Checked-out"])
            if st.button("🔄 Update Booking Status", use_container_width=True):
                booking["status"] = new_status
                st.success(f"{selected} updated to {new_status}.")
        else:
            st.info("No active booking.")

# =========================
# ROOM MANAGEMENT
# =========================
elif page == "🛏️ Room Management":
    st.subheader("🛏️ Staff Room Management")

    st.dataframe(room_df(), use_container_width=True, hide_index=True)

    st.divider()

    # ---------- ADD NEW ROOM ----------
    st.markdown("### ➕ Add New Room")

    a, b, c = st.columns(3)
    add_room_no = a.number_input(
        "New Room Number",
        min_value=1,
        max_value=9999,
        value=501,
        step=1,
        key="add_room_no"
    )
    room_type_options = ["Economy", "Standard", "Premium", "Deluxe", "Suite", "Custom"]

    add_type = b.selectbox(
        "Room Type / Category",
        room_type_options,
        key="add_room_type"
    )

    custom_type = ""
    if add_type == "Custom":
        custom_type = b.text_input(
            "Enter Custom Category",
            placeholder="e.g. Family, Executive, Presidential",
            key="custom_room_type"
        ).strip()

    add_rate = c.number_input(
        "Price / Night",
        min_value=500,
        max_value=50000,
        value=5000,
        step=500,
        key="add_room_rate"
    )

    if st.button("➕ Add Room", use_container_width=True):
        add_room_no = int(add_room_no)
        final_type = custom_type if add_type == "Custom" else add_type

        if add_room_no in st.session_state.rooms:
            st.error(f"Room {add_room_no} already exists.")
        elif not final_type:
            st.error("Please enter a room category.")
        else:
            st.session_state.rooms[add_room_no] = {
                "type": final_type,
                "rate": add_rate,
                "status": "Available",
                "readiness": "Ready"
            }
            st.success(
                f"Room {add_room_no} added successfully! "
                f"Category: {final_type} • ₹{add_rate:,}/night"
            )

    st.divider()

    st.markdown("### ➕➕ Add Multiple Rooms at Once")
    st.caption("Useful when the hotel adds a new floor or several rooms together.")

    b1, b2, b3, b4 = st.columns(4)
    start_room = b1.number_input("Starting Room No.", 1, 9999, 501, key="bulk_start")
    room_count = b2.number_input("Number of Rooms", 1, 100, 2, key="bulk_count")
    bulk_type = b3.selectbox(
        "Category",
        ["Economy", "Standard", "Premium", "Deluxe", "Suite"],
        key="bulk_type"
    )
    bulk_rate = b4.number_input(
        "Price / Night",
        500, 50000, 5000, step=500, key="bulk_rate"
    )

    if st.button("➕ Add All Rooms", use_container_width=True):
        start_room = int(start_room)
        room_count = int(room_count)
        requested = list(range(start_room, start_room + room_count))
        duplicates = [r for r in requested if r in st.session_state.rooms]

        if duplicates:
            st.error(f"These room numbers already exist: {duplicates}")
        else:
            for room_no in requested:
                st.session_state.rooms[room_no] = {
                    "type": bulk_type,
                    "rate": bulk_rate,
                    "status": "Available",
                    "readiness": "Ready"
                }
            st.success(
                f"{room_count} rooms added successfully: "
                f"{requested[0]}–{requested[-1]} "
                f"({bulk_type}, ₹{bulk_rate:,}/night)."
            )

    st.divider()

    # ---------- EDIT EXISTING ROOM ----------
    st.markdown("### ✏️ Edit Room Type, Pricing & Availability")

    room_no = st.selectbox(
        "Select Room",
        sorted(st.session_state.rooms.keys()),
        key="edit_room_select"
    )
    current = st.session_state.rooms[room_no]

    a, b, c = st.columns(3)
    base_room_types = ["Economy", "Standard", "Premium", "Deluxe", "Suite"]
    existing_custom_types = sorted({
        r["type"] for r in st.session_state.rooms.values()
        if r["type"] not in base_room_types
    })
    room_types = base_room_types + existing_custom_types

    new_type = a.selectbox(
        "Room Type / Category",
        room_types,
        index=room_types.index(current["type"]) if current["type"] in room_types else 0,
        key="edit_room_type"
    )
    new_rate = b.number_input(
        "Price / Night",
        500,
        50000,
        int(current["rate"]),
        step=500,
        key="edit_room_rate"
    )
    room_statuses = ["Available", "Occupied", "Maintenance"]
    new_status = c.selectbox(
        "Room Status",
        room_statuses,
        index=room_statuses.index(current["status"]) if current["status"] in room_statuses else 0,
        key="edit_room_status"
    )

    if st.button("💾 Update Room", use_container_width=True):
        current["type"] = new_type
        current["rate"] = new_rate
        current["status"] = new_status
        st.success(f"Room {room_no} updated successfully.")

    # ---------- REMOVE ROOM ----------
    st.divider()
    st.markdown("### 🗑️ Remove Room")

    remove_room = st.selectbox(
        "Select Room to Remove",
        sorted(st.session_state.rooms.keys()),
        key="remove_room_select"
    )

    if st.button("🗑️ Remove Selected Room", use_container_width=True):
        if st.session_state.rooms[remove_room]["status"] == "Occupied":
            st.error("Occupied room cannot be removed. Check out the guest first.")
        else:
            del st.session_state.rooms[remove_room]
            st.success(f"Room {remove_room} removed successfully.")
            st.rerun()

# =========================
# HOUSEKEEPING
# =========================
elif page == "🧹 Housekeeping":
    st.subheader("🧹 Housekeeping & Room Readiness")

    st.info("Staff can assign cleaning tasks and update room-readiness in real time.")

    room_no = st.selectbox("Room", list(st.session_state.rooms.keys()))
    staff = st.selectbox("Assign Staff", HOUSEKEEPING_STAFF)
    task = st.selectbox("Task", ["Cleaning", "Inspection", "Deep Cleaning", "Maintenance Check"])
    status = st.selectbox("Task Status", ["Assigned", "In Progress", "Completed"])

    if st.button("🧹 Assign / Update Task", use_container_width=True):
        set_housekeeping(room_no, task, staff, status)
        if status == "Completed":
            st.session_state.rooms[room_no]["readiness"] = "Ready"
        else:
            st.session_state.rooms[room_no]["readiness"] = "Cleaning"
        st.success(f"Housekeeping task updated for Room {room_no}.")

    st.divider()
    st.markdown("### Current Housekeeping Tasks")
    if st.session_state.housekeeping:
        st.dataframe(st.session_state.housekeeping, use_container_width=True, hide_index=True)
    else:
        st.info("No housekeeping tasks assigned.")

    st.markdown("### Room Readiness")
    readiness = [{
        "Room": room_no,
        "Occupancy": data["status"],
        "Readiness": data["readiness"]
    } for room_no, data in st.session_state.rooms.items()]
    st.dataframe(readiness, use_container_width=True, hide_index=True)

# =========================
# BILLING & PAYMENTS
# =========================
elif page == "💰 Billing & Payments":
    st.subheader("💰 Billing, Discounts, Taxes & Payments")

    active = active_bookings()
    if not active:
        st.info("No active bookings.")
    else:
        selected = st.selectbox("Select Booking", [b["booking_id"] for b in active], key="bill_id")
        b = find_booking(selected)

        food_total = 0
        service_total = 0

        st.markdown("### Additional Charges")
        c1, c2 = st.columns(2)
        food_item = c1.selectbox("Food", list(FOOD.keys()), key="bill_food")
        food_qty = c1.number_input("Food Quantity", 1, 20, 1, key="bill_food_qty")
        service_item = c2.selectbox("Service", list(SERVICES.keys()), key="bill_service")
        service_qty = c2.number_input("Service Quantity", 1, 20, 1, key="bill_service_qty")

        if st.button("➕ Add Charges"):
            b["food_total"] = b.get("food_total", 0) + FOOD[food_item] * food_qty
            b["service_total"] = b.get("service_total", 0) + SERVICES[service_item] * service_qty
            st.success("Additional charges added.")

        food_total = b.get("food_total", 0)
        service_total = b.get("service_total", 0)
        room_total = b["room_total"]
        discount_amount = room_total * b["discount"] / 100
        taxable = room_total - discount_amount + food_total + service_total
        tax = taxable * 0.05
        grand = taxable + tax

        bill = [
            {"Particular": "Room Charges", "Amount": f"₹{room_total:,.2f}"},
            {"Particular": "Food", "Amount": f"₹{food_total:,.2f}"},
            {"Particular": "Hotel Services", "Amount": f"₹{service_total:,.2f}"},
            {"Particular": f"Discount ({b['discount']:.0f}%)", "Amount": f"-₹{discount_amount:,.2f}"},
            {"Particular": "GST (5%)", "Amount": f"₹{tax:,.2f}"},
            {"Particular": "GRAND TOTAL", "Amount": f"₹{grand:,.2f}"}
        ]
        st.table(bill)

        method = st.selectbox("Payment Method", ["UPI", "Card", "Cash"])
        if st.button("💳 Record Payment", use_container_width=True):
            payment_id = "PAY-" + uuid.uuid4().hex[:6].upper()
            st.session_state.payments.append({
                "payment_id": payment_id,
                "booking_id": b["booking_id"],
                "guest": b["guest"],
                "amount": grand,
                "method": method,
                "status": "Paid",
                "date": datetime.now().strftime("%d-%m-%Y %H:%M")
            })
            b["payment_status"] = "Paid"
            b["final_total"] = grand
            st.success(f"Payment recorded: {payment_id} | ₹{grand:,.2f} via {method}")

        st.divider()
        st.markdown("### Payment Records")
        if st.session_state.payments:
            st.dataframe(st.session_state.payments, use_container_width=True, hide_index=True)
        else:
            st.info("No payment records yet.")

# =========================
# RECORDS
# =========================
elif page == "📋 Records":
    st.subheader("📋 Hotel Records")

    t1, t2, t3 = st.tabs(["Bookings", "Payments", "Housekeeping"])

    with t1:
        if st.session_state.bookings:
            st.dataframe(st.session_state.bookings, use_container_width=True, hide_index=True)
        else:
            st.info("No bookings.")

    with t2:
        if st.session_state.payments:
            st.dataframe(st.session_state.payments, use_container_width=True, hide_index=True)
        else:
            st.info("No payments.")

    with t3:
        if st.session_state.housekeeping:
            st.dataframe(st.session_state.housekeeping, use_container_width=True, hide_index=True)
        else:
            st.info("No housekeeping records.")

st.divider()
st.caption("Hotel Management System | Python + Streamlit | Academic Project")
