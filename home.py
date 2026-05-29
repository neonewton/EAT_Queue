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
    layout="centered"
)


# =========================================================
# CONSTANTS
# =========================================================
LOCATIONS = ["Male", "Female", "Handicap"]
GENDERS = ["Male", "Female"]
ACTIVE_STATUSES = ["Queued", "Returned"]
SGT = ZoneInfo("Asia/Singapore")


# =========================================================
# MOBILE-FIRST CSS
# =========================================================
st.markdown(
    """
    <style>
    .block-container {
        padding-top: 0.8rem;
        padding-left: 0.7rem;
        padding-right: 0.7rem;
        max-width: 520px;
    }

    h1 {
        font-size: 1.65rem !important;
        text-align: center;
        margin-bottom: 0.5rem;
    }

    h2, h3 {
        margin-top: 0.4rem;
        margin-bottom: 0.4rem;
    }

    div[data-testid="stButton"] > button {
        width: 100%;
        min-height: 48px;
        font-size: 17px;
        font-weight: 600;
        border-radius: 12px;
        padding: 0.4rem 0.5rem;
    }

    div[data-testid="stHorizontalBlock"] {
        gap: 0.35rem;
    }

    .seat-display {
        border: 2px solid #dddddd;
        border-radius: 14px;
        text-align: center;
        padding: 0.7rem;
        margin-bottom: 0.6rem;
        font-size: 2.2rem;
        font-weight: 800;
        background-color: #fafafa;
    }

    .section-card {
        border: 1px solid #e3e3e3;
        border-radius: 16px;
        padding: 0.75rem;
        margin-bottom: 0.75rem;
        background-color: #ffffff;
    }

    .queue-card {
        border: 1px solid #dddddd;
        border-radius: 16px;
        padding: 0.75rem;
        margin-bottom: 0.7rem;
        background-color: #fafafa;
    }

    .queue-card-returned {
        border: 1px solid #b7e0b7;
        border-radius: 16px;
        padding: 0.75rem;
        margin-bottom: 0.7rem;
        background-color: #f0fff0;
    }

    .queue-code {
        font-size: 1.7rem;
        font-weight: 800;
        margin-bottom: 0.2rem;
    }

    .queue-meta {
        font-size: 0.9rem;
        color: #555555;
        line-height: 1.45;
    }

    .lane-header {
        text-align: center;
        font-size: 1.35rem;
        font-weight: 800;
        padding: 0.5rem;
        border-radius: 14px;
        background-color: #f3f3f3;
        margin-bottom: 0.6rem;
    }

    .preview-box {
        text-align: center;
        font-size: 1.2rem;
        font-weight: 700;
        padding: 0.5rem;
        border-radius: 12px;
        background-color: #f5f5f5;
        margin-top: 0.5rem;
        margin-bottom: 0.5rem;
    }

    .small-note {
        text-align: center;
        font-size: 0.85rem;
        color: #666666;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# PASSWORD PROTECTION
# =========================================================
st.title("🚻 Toilet Queue")

try:
    APP_PASSWORD = st.secrets["APP_PASSWORD"]
except KeyError:
    st.error("APP_PASSWORD is missing from Streamlit Cloud Secrets.")
    st.stop()

password = st.text_input("Enter event password", type="password")

if password != APP_PASSWORD:
    st.warning("Please enter the correct password to continue.")
    st.stop()


# =========================================================
# SUPABASE CONNECTION
# =========================================================
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except KeyError:
    st.error("SUPABASE_URL or SUPABASE_KEY is missing from Streamlit Cloud Secrets.")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# =========================================================
# SESSION STATE
# =========================================================
if "seat_no_text" not in st.session_state:
    st.session_state.seat_no_text = ""

if "selected_gender" not in st.session_state:
    st.session_state.selected_gender = "Male"

if "selected_location" not in st.session_state:
    st.session_state.selected_location = "Male"

if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

if "last_action_message" not in st.session_state:
    st.session_state.last_action_message = ""


# =========================================================
# HELPER FUNCTIONS
# =========================================================
def now_utc_iso():
    return datetime.now(timezone.utc).isoformat()


def format_datetime(dt_string):
    if not dt_string:
        return "-"

    try:
        dt = datetime.fromisoformat(str(dt_string).replace("Z", "+00:00"))
        dt_sgt = dt.astimezone(SGT)
        return dt_sgt.strftime("%I:%M:%S %p")
    except Exception:
        return str(dt_string)


def get_queue_code(seat_no, gender):
    prefix = "M" if gender == "Male" else "F"
    return f"{prefix}{seat_no}"


def safe_execute(query, error_message):
    try:
        return query.execute().data
    except Exception as e:
        st.error(error_message)
        st.exception(e)
        return None


def archive_old_returned():
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=10)

    returned_rows = safe_execute(
        supabase.table("toilet_queue")
        .select("*")
        .eq("status", "Returned"),
        "Failed to check returned queue records."
    )

    if returned_rows is None:
        return

    for row in returned_rows:
        returned_at_raw = row.get("returned_at")

        if not returned_at_raw:
            continue

        try:
            returned_at = datetime.fromisoformat(
                str(returned_at_raw).replace("Z", "+00:00")
            )

            if returned_at < cutoff:
                safe_execute(
                    supabase.table("toilet_queue")
                    .update({"status": "Archived"})
                    .eq("id", row["id"]),
                    "Failed to archive old returned record."
                )

        except Exception:
            continue


def load_queue(location):
    rows = safe_execute(
        supabase.table("toilet_queue")
        .select("*")
        .eq("location", location)
        .in_("status", ACTIVE_STATUSES)
        .order("queue_order")
        .order("assigned_at"),
        f"Failed to load {location} queue from Supabase."
    )

    return rows or []


def load_log():
    rows = safe_execute(
        supabase.table("toilet_queue")
        .select("*")
        .order("assigned_at", desc=True),
        "Failed to load queue log from Supabase."
    )

    return rows or []


def get_next_order(location):
    rows = safe_execute(
        supabase.table("toilet_queue")
        .select("queue_order")
        .eq("location", location)
        .in_("status", ACTIVE_STATUSES),
        f"Failed to get next queue order for {location}."
    )

    if not rows:
        return 1

    max_order = max(row.get("queue_order", 0) or 0 for row in rows)
    return max_order + 1


def add_student():
    seat_no = st.session_state.seat_no_text.strip()
    gender = st.session_state.selected_gender
    location = st.session_state.selected_location

    if not seat_no:
        st.session_state.last_action_message = "Please enter a seat number."
        return

    if not seat_no.isdigit():
        st.session_state.last_action_message = "Seat number must be numeric."
        return

    queue_code = get_queue_code(seat_no, gender)

    duplicate = safe_execute(
        supabase.table("toilet_queue")
        .select("*")
        .eq("queue_code", queue_code)
        .in_("status", ACTIVE_STATUSES),
        "Failed to check duplicate queue record."
    )

    if duplicate:
        st.session_state.last_action_message = f"{queue_code} is already active."
        return

    next_order = get_next_order(location)

    result = safe_execute(
        supabase.table("toilet_queue")
        .insert({
            "queue_code": queue_code,
            "seat_no": int(seat_no),
            "gender": gender,
            "location": location,
            "status": "Queued",
            "queue_order": next_order,
            "assigned_at": now_utc_iso(),
            "returned_at": None
        }),
        "Failed to add student to queue."
    )

    if result is not None:
        st.session_state.last_action_message = f"Added {queue_code} to {location}."
        st.session_state.seat_no_text = ""


def mark_returned(row_id, queue_code):
    result = safe_execute(
        supabase.table("toilet_queue")
        .update({
            "status": "Returned",
            "returned_at": now_utc_iso()
        })
        .eq("id", row_id),
        f"Failed to mark {queue_code} as returned. Check Supabase UPDATE permission."
    )

    if result is not None:
        st.session_state.last_action_message = f"{queue_code} returned."


def swap_queue_order(row_a, row_b):
    id_a = row_a["id"]
    id_b = row_b["id"]
    order_a = row_a["queue_order"]
    order_b = row_b["queue_order"]

    safe_execute(
        supabase.table("toilet_queue")
        .update({"queue_order": order_b})
        .eq("id", id_a),
        "Failed to update queue order."
    )

    safe_execute(
        supabase.table("toilet_queue")
        .update({"queue_order": order_a})
        .eq("id", id_b),
        "Failed to update queue order."
    )


def move_up(location, row_id):
    queue = [
        row for row in load_queue(location)
        if row.get("status") == "Queued"
    ]

    for index, row in enumerate(queue):
        if row["id"] == row_id:
            if index > 0:
                swap_queue_order(row, queue[index - 1])
            return


def move_down(location, row_id):
    queue = [
        row for row in load_queue(location)
        if row.get("status") == "Queued"
    ]

    for index, row in enumerate(queue):
        if row["id"] == row_id:
            if index < len(queue) - 1:
                swap_queue_order(row, queue[index + 1])
            return


def append_digit(digit):
    if len(st.session_state.seat_no_text) < 4:
        st.session_state.seat_no_text += str(digit)


def backspace_digit():
    st.session_state.seat_no_text = st.session_state.seat_no_text[:-1]


def clear_digits():
    st.session_state.seat_no_text = ""


def select_gender(gender):
    st.session_state.selected_gender = gender


def select_location(location):
    st.session_state.selected_location = location


# =========================================================
# AUTO ARCHIVE + AUTO REFRESH
# =========================================================
archive_old_returned()

if time.time() - st.session_state.last_refresh > 3:
    st.session_state.last_refresh = time.time()
    st.rerun()


# =========================================================
# ADD STUDENT SECTION
# =========================================================
st.markdown("<div class='section-card'>", unsafe_allow_html=True)
st.subheader("➕ Add Student")

seat_display = st.session_state.seat_no_text or "—"
st.markdown(
    f"<div class='seat-display'>{seat_display}</div>",
    unsafe_allow_html=True
)

# Dial pad
pad_rows = [
    ["1", "2", "3"],
    ["4", "5", "6"],
    ["7", "8", "9"],
    ["C", "0", "⌫"]
]

for row in pad_rows:
    c1, c2, c3 = st.columns(3)

    for col, key in zip([c1, c2, c3], row):
        with col:
            if key == "C":
                st.button(
                    "C",
                    key="pad_clear",
                    on_click=clear_digits
                )
            elif key == "⌫":
                st.button(
                    "⌫",
                    key="pad_backspace",
                    on_click=backspace_digit
                )
            else:
                st.button(
                    key,
                    key=f"pad_{key}",
                    on_click=append_digit,
                    args=(key,)
                )

st.markdown("### Gender")
g1, g2 = st.columns(2)

with g1:
    st.button(
        "Male",
        key="gender_male",
        type="primary" if st.session_state.selected_gender == "Male" else "secondary",
        on_click=select_gender,
        args=("Male",)
    )

with g2:
    st.button(
        "Female",
        key="gender_female",
        type="primary" if st.session_state.selected_gender == "Female" else "secondary",
        on_click=select_gender,
        args=("Female",)
    )

st.markdown("### Assign To")
l1, l2, l3 = st.columns(3)

with l1:
    st.button(
        "Male",
        key="location_male",
        type="primary" if st.session_state.selected_location == "Male" else "secondary",
        on_click=select_location,
        args=("Male",)
    )

with l2:
    st.button(
        "Female",
        key="location_female",
        type="primary" if st.session_state.selected_location == "Female" else "secondary",
        on_click=select_location,
        args=("Female",)
    )

with l3:
    st.button(
        "Handicap",
        key="location_handicap",
        type="primary" if st.session_state.selected_location == "Handicap" else "secondary",
        on_click=select_location,
        args=("Handicap",)
    )

preview_code = (
    get_queue_code(
        st.session_state.seat_no_text,
        st.session_state.selected_gender
    )
    if st.session_state.seat_no_text
    else "-"
)

st.markdown(
    f"<div class='preview-box'>Queue Code: {preview_code}</div>",
    unsafe_allow_html=True
)

st.button(
    "Add to Queue",
    key="add_to_queue",
    type="primary",
    on_click=add_student
)

if st.session_state.last_action_message:
    st.info(st.session_state.last_action_message)

st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# ACTIVE QUEUE SECTION — PHONE-FIRST TABS
# =========================================================
st.subheader("📋 Active Queue")

tabs = st.tabs(["🚹 Male", "🚺 Female", "♿ Handicap"])

for tab, location in zip(tabs, LOCATIONS):
    with tab:
        st.markdown(
            f"<div class='lane-header'>{location} Toilet</div>",
            unsafe_allow_html=True
        )

        queue = load_queue(location)

        if not queue:
            st.info("No active queue.")
            continue

        for index, row in enumerate(queue, start=1):
            row_id = row.get("id")
            queue_code = row.get("queue_code", "")
            seat = row.get("seat_no", "")
            status = row.get("status", "Queued")
            assigned_at = format_datetime(row.get("assigned_at"))
            returned_at = format_datetime(row.get("returned_at"))

            card_class = (
                "queue-card-returned"
                if status == "Returned"
                else "queue-card"
            )

            st.markdown(
                f"<div class='{card_class}'>",
                unsafe_allow_html=True
            )

            if status == "Returned":
                code_display = f"✅ {queue_code}"
            else:
                code_display = f"{index}. {queue_code}"

            st.markdown(
                f"<div class='queue-code'>{code_display}</div>",
                unsafe_allow_html=True
            )

            st.markdown(
                f"""
                <div class='queue-meta'>
                    Seat: {seat}<br>
                    Status: {status}<br>
                    Assigned: {assigned_at}<br>
                    Returned: {returned_at}
                </div>
                """,
                unsafe_allow_html=True
            )

            b1, b2, b3 = st.columns([1, 1, 2])

            with b1:
                st.button(
                    "⬆️",
                    key=f"up_{location}_{row_id}",
                    disabled=(status != "Queued"),
                    on_click=move_up,
                    args=(location, row_id)
                )

            with b2:
                st.button(
                    "⬇️",
                    key=f"down_{location}_{row_id}",
                    disabled=(status != "Queued"),
                    on_click=move_down,
                    args=(location, row_id)
                )

            with b3:
                if status == "Queued":
                    st.button(
                        "Return",
                        key=f"return_{location}_{row_id}",
                        type="primary",
                        on_click=mark_returned,
                        args=(row_id, queue_code)
                    )
                else:
                    st.caption("Returned — will hide after 10 seconds")

            st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# LOG SECTION
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
            "returned_at"
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