import time
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
from supabase import create_client


# =========================================================
# STREAMLIT CONFIG
# =========================================================
st.set_page_config(
    page_title="Toilet Queue System",
    page_icon="🚻",
    layout="wide"
)


# =========================================================
# CONSTANTS
# =========================================================
LOCATIONS = ["Male", "Female", "Handicap"]
GENDERS = ["Male", "Female"]
ACTIVE_STATUSES = ["Queued", "Returned"]
SGT = ZoneInfo("Asia/Singapore")


# =========================================================
# PASSWORD PROTECTION
# =========================================================
st.title("🚻 Toilet Queue System")

# password = st.text_input("Enter event password", type="password")

# if password != st.secrets["APP_PASSWORD"]:
#     st.warning("Please enter the correct password to continue.")
#     st.stop()


# =========================================================
# SUPABASE CONNECTION
# =========================================================
NEXT_PUBLIC_SUPABASE_URL = st.secrets["SUPABASE_URL"]
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY)

# =========================================================
# HELPER FUNCTIONS
# =========================================================
def now_utc_iso():
    """Return current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def format_datetime(dt_string):
    """Convert Supabase timestamp string to Singapore time display."""
    if not dt_string:
        return "-"

    try:
        dt = datetime.fromisoformat(dt_string.replace("Z", "+00:00"))
        dt_sgt = dt.astimezone(SGT)
        return dt_sgt.strftime("%I:%M:%S %p")
    except Exception:
        return dt_string


def archive_old_returned():
    """
    Auto-hide returned students after 10 seconds.
    This does not delete the record. It changes status to Archived.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=10)

    returned_rows = (
        supabase.table("toilet_queue")
        .select("*")
        .eq("status", "Returned")
        .execute()
        .data
    )

    for row in returned_rows:
        returned_at_raw = row.get("returned_at")

        if not returned_at_raw:
            continue

        try:
            returned_at = datetime.fromisoformat(
                returned_at_raw.replace("Z", "+00:00")
            )

            if returned_at < cutoff:
                supabase.table("toilet_queue").update({
                    "status": "Archived"
                }).eq("id", row["id"]).execute()

        except Exception:
            pass


def load_queue(location):
    """Load active queue for one location."""
    return (
        supabase.table("toilet_queue")
        .select("*")
        .eq("location", location)
        .in_("status", ACTIVE_STATUSES)
        .order("queue_order")
        .execute()
        .data
    )


def load_all_active():
    """Load all active records."""
    return (
        supabase.table("toilet_queue")
        .select("*")
        .in_("status", ACTIVE_STATUSES)
        .order("location")
        .order("queue_order")
        .execute()
        .data
    )


def load_log():
    """Load all records, including archived records."""
    return (
        supabase.table("toilet_queue")
        .select("*")
        .order("assigned_at", desc=True)
        .execute()
        .data
    )


def get_next_order(location):
    """Get next queue order number for selected location."""
    existing = (
        supabase.table("toilet_queue")
        .select("*")
        .eq("location", location)
        .eq("status", "Queued")
        .execute()
        .data
    )

    if not existing:
        return 1

    max_order = max(row.get("queue_order", 0) or 0 for row in existing)
    return max_order + 1


def add_student(seat_no, gender, location, remarks=""):
    """Add student to queue."""
    prefix = "M" if gender == "Male" else "F"
    queue_code = f"{prefix}{seat_no}"

    # Prevent duplicate active queue entry for same queue code
    duplicate = (
        supabase.table("toilet_queue")
        .select("*")
        .eq("queue_code", queue_code)
        .in_("status", ACTIVE_STATUSES)
        .execute()
        .data
    )

    if duplicate:
        st.error(f"{queue_code} is already in the active queue.")
        return

    next_order = get_next_order(location)

    supabase.table("toilet_queue").insert({
        "queue_code": queue_code,
        "seat_no": int(seat_no),
        "gender": gender,
        "location": location,
        "status": "Queued",
        "queue_order": next_order,
        "assigned_at": now_utc_iso(),
        "returned_at": None,
        "remarks": remarks
    }).execute()

    st.success(f"Added {queue_code} to {location} queue.")


def mark_returned(row_id):
    """Mark student as returned."""
    supabase.table("toilet_queue").update({
        "status": "Returned",
        "returned_at": now_utc_iso()
    }).eq("id", row_id).execute()


def swap_queue_order(row_a, row_b):
    """Swap queue order between two rows."""
    order_a = row_a["queue_order"]
    order_b = row_b["queue_order"]

    supabase.table("toilet_queue").update({
        "queue_order": order_b
    }).eq("id", row_a["id"]).execute()

    supabase.table("toilet_queue").update({
        "queue_order": order_a
    }).eq("id", row_b["id"]).execute()


def move_up(location, row_id):
    """Move selected queue item up within same location."""
    queue = load_queue(location)

    for index, row in enumerate(queue):
        if row["id"] == row_id and index > 0:
            swap_queue_order(row, queue[index - 1])
            return


def move_down(location, row_id):
    """Move selected queue item down within same location."""
    queue = load_queue(location)

    for index, row in enumerate(queue):
        if row["id"] == row_id and index < len(queue) - 1:
            swap_queue_order(row, queue[index + 1])
            return


def delete_archived_records():
    """
    Optional hard delete archived records.
    Not used by default because keeping records is better for audit trail.
    """
    supabase.table("toilet_queue").delete().eq("status", "Archived").execute()


# =========================================================
# AUTO ARCHIVE OLD RETURNED RECORDS
# =========================================================
try:
    archive_old_returned()
except Exception as e:
    st.warning("Archive check skipped. Please check Supabase table or permissions.")


# =========================================================
# AUTO REFRESH
# =========================================================
# This reruns the app every 3 seconds so returned students disappear after 10 seconds.
# No extra package required.
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

if time.time() - st.session_state.last_refresh > 3:
    st.session_state.last_refresh = time.time()
    st.rerun()


# =========================================================
# ADD STUDENT FORM
# =========================================================
st.subheader("➕ Add Student to Queue")

with st.form("add_student_form", clear_on_submit=True):
    col1, col2, col3 = st.columns(3)

    with col1:
        seat_no = st.number_input("Seat Number", min_value=1, step=1)

    with col2:
        gender = st.selectbox("Gender", GENDERS)

    with col3:
        location = st.selectbox("Assign to", LOCATIONS)

    remarks = st.text_input("Remarks Optional")

    submitted = st.form_submit_button("Add to Queue")

    if submitted:
        add_student(seat_no, gender, location, remarks)
        st.rerun()


st.divider()


# =========================================================
# ACTIVE QUEUE DISPLAY
# =========================================================
st.subheader("📋 Active Toilet Queue")

tabs = st.tabs(["🚹 Male", "🚺 Female", "♿ Handicap"])

for tab, location in zip(tabs, LOCATIONS):
    with tab:
        queue = load_queue(location)

        if not queue:
            st.info(f"No active queue for {location}.")
            continue

        for index, row in enumerate(queue, start=1):
            status = row.get("status", "Queued")
            queue_code = row.get("queue_code", "")
            seat = row.get("seat_no", "")
            assigned_at = format_datetime(row.get("assigned_at"))
            returned_at = format_datetime(row.get("returned_at"))
            remarks = row.get("remarks", "")

            with st.container(border=True):
                top_col1, top_col2, top_col3, top_col4 = st.columns([1, 2, 2, 2])

                with top_col1:
                    st.markdown(f"### {index}")

                with top_col2:
                    if status == "Returned":
                        st.markdown(f"### ✅ {queue_code}")
                    else:
                        st.markdown(f"### {queue_code}")

                    st.caption(f"Seat {seat}")

                with top_col3:
                    st.write(f"**Status:** {status}")
                    st.write(f"**Assigned:** {assigned_at}")

                    if status == "Returned":
                        st.write(f"**Returned:** {returned_at}")

                with top_col4:
                    if remarks:
                        st.write(f"**Remarks:** {remarks}")

                button_col1, button_col2, button_col3 = st.columns(3)

                with button_col1:
                    if st.button("⬆️ Up", key=f"up_{location}_{row['id']}"):
                        move_up(location, row["id"])
                        st.rerun()

                with button_col2:
                    if st.button("⬇️ Down", key=f"down_{location}_{row['id']}"):
                        move_down(location, row["id"])
                        st.rerun()

                with button_col3:
                    if status == "Queued":
                        if st.button("✅ Return", key=f"return_{location}_{row['id']}"):
                            mark_returned(row["id"])
                            st.rerun()
                    else:
                        st.caption("Will hide after 10 seconds")


st.divider()


# =========================================================
# ADMIN / LOG SECTION
# =========================================================
with st.expander("📊 View Queue Log / Export CSV"):
    log_rows = load_log()

    if not log_rows:
        st.info("No records yet.")
    else:
        df = pd.DataFrame(log_rows)

        display_columns = [
            "queue_code",
            "seat_no",
            "gender",
            "location",
            "status",
            "queue_order",
            "assigned_at",
            "returned_at",
            "remarks"
        ]

        existing_columns = [col for col in display_columns if col in df.columns]
        df_display = df[existing_columns].copy()

        if "assigned_at" in df_display.columns:
            df_display["assigned_at"] = df_display["assigned_at"].apply(format_datetime)

        if "returned_at" in df_display.columns:
            df_display["returned_at"] = df_display["returned_at"].apply(format_datetime)

        st.dataframe(df_display, use_container_width=True)

        csv = df.to_csv(index=False).encode("utf-8-sig")

        st.download_button(
            label="Download Full Log as CSV",
            data=csv,
            file_name="toilet_queue_log.csv",
            mime="text/csv"
        )