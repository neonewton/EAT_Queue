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
    page_title="Toilet Queue",
    page_icon="🚻",
    layout="centered",
    initial_sidebar_state="collapsed",
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
    /* Overall mobile container */
    .block-container {
        max-width: 430px !important;
        padding-top: 0.75rem !important;
        padding-left: 0.75rem !important;
        padding-right: 0.75rem !important;
        padding-bottom: 1rem !important;
    }

    h1 {
        text-align: center !important;
        font-size: 1.55rem !important;
        margin-bottom: 0.75rem !important;
    }

    h2, h3 {
        margin-top: 0.6rem !important;
        margin-bottom: 0.45rem !important;
    }

    /* Make all Streamlit buttons large and touch-friendly */
    .stButton > button {
        width: 100% !important;
        min-height: 54px !important;
        border-radius: 14px !important;
        font-size: 1.05rem !important;
        font-weight: 700 !important;
        padding: 0.55rem 0.4rem !important;
    }

    button[kind="primary"] {
        font-weight: 800 !important;
    }

    /* Reduce column gaps for keypad */
    div[data-testid="stHorizontalBlock"] {
        gap: 0.45rem !important;
    }

    /* Seat number display */
    .seat-display {
        width: 100%;
        border: 2px solid #d9d9d9;
        border-radius: 18px;
        text-align: center;
        padding: 0.85rem 0;
        margin: 0.4rem 0 0.75rem 0;
        font-size: 2.4rem;
        font-weight: 900;
        background-color: #fafafa;
        letter-spacing: 0.08rem;
    }

    /* Section card */
    .section-card {
        border: 1px solid #e5e5e5;
        border-radius: 18px;
        padding: 0.85rem;
        margin-bottom: 0.9rem;
        background-color: #ffffff;
    }

    /* Preview */
    .preview-box {
        width: 100%;
        text-align: center;
        font-size: 1.15rem;
        font-weight: 800;
        padding: 0.8rem 0;
        border-radius: 14px;
        background-color: #f3f3f3;
        margin: 0.85rem 0;
    }

    /* Queue cards */
    .queue-card {
        border: 1px solid #dedede;
        border-radius: 18px;
        padding: 0.9rem;
        margin-bottom: 0.8rem;
        background-color: #ffffff;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    }

    .queue-card-returned {
        border: 1px solid #9cd89c;
        border-radius: 18px;
        padding: 0.9rem;
        margin-bottom: 0.8rem;
        background-color: #f1fff1;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    }

    .queue-code {
        font-size: 1.85rem;
        font-weight: 900;
        margin-bottom: 0.35rem;
    }

    .queue-meta {
        font-size: 0.9rem;
        color: #555;
        line-height: 1.55;
        margin-bottom: 0.75rem;
    }

    .lane-header {
        text-align: center;
        font-size: 1.2rem;
        font-weight: 900;
        padding: 0.75rem 0;
        border-radius: 16px;
        background-color: #f2f2f2;
        margin-bottom: 0.8rem;
    }

    .success-note {
        text-align: center;
        font-weight: 700;
        padding: 0.6rem;
        border-radius: 12px;
        background-color: #f4f4f4;
        margin-bottom: 0.6rem;
    }

    /* Make radio options nicer on mobile */
    div[role="radiogroup"] {
        gap: 0.5rem;
    }

    div[role="radiogroup"] label {
        border: 1px solid #ddd;
        border-radius: 14px;
        padding: 0.55rem 0.75rem;
        background-color: #fafafa;
        margin-bottom: 0.35rem;
    }

    /* Hide Streamlit default menu/footer */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
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

password = st.text_input("Event Password", type="password", label_visibility="collapsed")

if password != APP_PASSWORD:
    st.warning("Enter password to continue.")
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


def db_execute(query, error_message):
    try:
        response = query.execute()
        return response.data
    except Exception as e:
        st.error(error_message)
        st.exception(e)
        return None


def archive_old_returned():
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=10)

    returned_rows = db_execute(
        supabase.table("toilet_queue")
        .select("*")
        .eq("status", "Returned"),
        "Failed to check returned queue records.",
    )

    if not returned_rows:
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
                db_execute(
                    supabase.table("toilet_queue")
                    .update({"status": "Archived"})
                    .eq("id", row["id"]),
                    "Failed to archive returned record.",
                )

        except Exception:
            continue


def load_queue(location):
    rows = db_execute(
        supabase.table("toilet_queue")
        .select("*")
        .eq("location", location)
        .in_("status", ACTIVE_STATUSES)
        .order("queue_order")
        .order("assigned_at"),
        f"Failed to load {location} queue.",
    )

    return rows or []


def load_log():
    rows = db_execute(
        supabase.table("toilet_queue")
        .select("*")
        .order("assigned_at", desc=True),
        "Failed to load queue log.",
    )

    return rows or []


def get_next_order(location):
    rows = db_execute(
        supabase.table("toilet_queue")
        .select("queue_order")
        .eq("location", location)
        .in_("status", ACTIVE_STATUSES),
        f"Failed to get next order for {location}.",
    )

    if not rows:
        return 1

    return max(row.get("queue_order", 0) or 0 for row in rows) + 1


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

    duplicate = db_execute(
        supabase.table("toilet_queue")
        .select("*")
        .eq("queue_code", queue_code)
        .in_("status", ACTIVE_STATUSES),
        "Failed to check duplicate record.",
    )

    if duplicate:
        st.session_state.last_action_message = f"{queue_code} is already active."
        return

    next_order = get_next_order(location)

    result = db_execute(
        supabase.table("toilet_queue")
        .insert({
            "queue_code": queue_code,
            "seat_no": int(seat_no),
            "gender": gender,
            "location": location,
            "status": "Queued",
            "queue_order": next_order,
            "assigned_at": now_utc_iso(),
            "returned_at": None,
        }),
        "Failed to add student.",
    )

    if result is not None:
        st.session_state.last_action_message = f"Added {queue_code} to {location}."
        st.session_state.seat_no_text = ""


def mark_returned(row_id, queue_code):
    result = db_execute(
        supabase.table("toilet_queue")
        .update({
            "status": "Returned",
            "returned_at": now_utc_iso(),
        })
        .eq("id", row_id)
        .select("*"),
        f"Failed to mark {queue_code} as returned.",
    )

    if result is not None:
        st.session_state.last_action_message = f"{queue_code} returned."


def swap_queue_order(row_a, row_b):
    order_a = row_a["queue_order"]
    order_b = row_b["queue_order"]

    db_execute(
        supabase.table("toilet_queue")
        .update({"queue_order": order_b})
        .eq("id", row_a["id"])
        .select("*"),
        "Failed to move queue item.",
    )

    db_execute(
        supabase.table("toilet_queue")
        .update({"queue_order": order_a})
        .eq("id", row_b["id"])
        .select("*"),
        "Failed to move queue item.",
    )


def move_up(location, row_id):
    queue = [row for row in load_queue(location) if row.get("status") == "Queued"]

    for index, row in enumerate(queue):
        if row["id"] == row_id and index > 0:
            swap_queue_order(row, queue[index - 1])
            st.session_state.last_action_message = f"{row['queue_code']} moved up."
            return


def move_down(location, row_id):
    queue = [row for row in load_queue(location) if row.get("status") == "Queued"]

    for index, row in enumerate(queue):
        if row["id"] == row_id and index < len(queue) - 1:
            swap_queue_order(row, queue[index + 1])
            st.session_state.last_action_message = f"{row['queue_code']} moved down."
            return


def append_digit(digit):
    if len(st.session_state.seat_no_text) < 4:
        st.session_state.seat_no_text += str(digit)


def backspace_digit():
    st.session_state.seat_no_text = st.session_state.seat_no_text[:-1]


def clear_digits():
    st.session_state.seat_no_text = ""


# =========================================================
# AUTO ARCHIVE + AUTO REFRESH
# =========================================================
archive_old_returned()

if time.time() - st.session_state.last_refresh > 4:
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
    unsafe_allow_html=True,
)

# Dial pad
pad_rows = [
    ["1", "2", "3"],
    ["4", "5", "6"],
    ["7", "8", "9"],
    ["C", "0", "⌫"],
]

for row_index, row in enumerate(pad_rows):
    cols = st.columns(3)

    for col, key in zip(cols, row):
        with col:
            if key == "C":
                st.button(
                    "C",
                    key=f"pad_clear_{row_index}",
                    on_click=clear_digits,
                )
            elif key == "⌫":
                st.button(
                    "⌫",
                    key=f"pad_backspace_{row_index}",
                    on_click=backspace_digit,
                )
            else:
                st.button(
                    key,
                    key=f"pad_{key}_{row_index}",
                    on_click=append_digit,
                    args=(key,),
                )

st.markdown("### Gender")

st.session_state.selected_gender = st.radio(
    "Gender",
    GENDERS,
    index=GENDERS.index(st.session_state.selected_gender),
    horizontal=True,
    label_visibility="collapsed",
)

st.markdown("### Assign To")

st.session_state.selected_location = st.radio(
    "Assign To",
    LOCATIONS,
    index=LOCATIONS.index(st.session_state.selected_location),
    horizontal=True,
    label_visibility="collapsed",
)

preview_code = (
    get_queue_code(st.session_state.seat_no_text, st.session_state.selected_gender)
    if st.session_state.seat_no_text
    else "-"
)

st.markdown(
    f"<div class='preview-box'>Queue Code: {preview_code}</div>",
    unsafe_allow_html=True,
)

st.button(
    "➕ Add to Queue",
    key="add_to_queue",
    type="primary",
    on_click=add_student,
)

if st.session_state.last_action_message:
    st.markdown(
        f"<div class='success-note'>{st.session_state.last_action_message}</div>",
        unsafe_allow_html=True,
    )

st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# ACTIVE QUEUE SECTION
# =========================================================
st.subheader("📋 Active Queue")

tabs = st.tabs(["🚹 Male", "🚺 Female", "♿ Handicap"])

for tab, location in zip(tabs, LOCATIONS):
    with tab:
        st.markdown(
            f"<div class='lane-header'>{location} Toilet</div>",
            unsafe_allow_html=True,
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

            card_class = "queue-card-returned" if status == "Returned" else "queue-card"

            st.markdown(
                f"<div class='{card_class}'>",
                unsafe_allow_html=True,
            )

            if status == "Returned":
                code_display = f"✅ {queue_code}"
            else:
                code_display = f"{index}. {queue_code}"

            st.markdown(
                f"<div class='queue-code'>{code_display}</div>",
                unsafe_allow_html=True,
            )

            st.markdown(
                f"""
                <div class='queue-meta'>
                    <b>Seat:</b> {seat}<br>
                    <b>Status:</b> {status}<br>
                    <b>Assigned:</b> {assigned_at}<br>
                    <b>Returned:</b> {returned_at}
                </div>
                """,
                unsafe_allow_html=True,
            )

            action_cols = st.columns([1, 1, 2])

            with action_cols[0]:
                st.button(
                    "⬆️",
                    key=f"up_{location}_{row_id}",
                    disabled=(status != "Queued"),
                    on_click=move_up,
                    args=(location, row_id),
                )

            with action_cols[1]:
                st.button(
                    "⬇️",
                    key=f"down_{location}_{row_id}",
                    disabled=(status != "Queued"),
                    on_click=move_down,
                    args=(location, row_id),
                )

            with action_cols[2]:
                st.button(
                    "✅ Return" if status == "Queued" else "Returned",
                    key=f"return_{location}_{row_id}",
                    type="primary" if status == "Queued" else "secondary",
                    disabled=(status != "Queued"),
                    on_click=mark_returned,
                    args=(row_id, queue_code),
                )

            if status == "Returned":
                st.caption("Will hide after 10 seconds.")

            st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# LOG SECTION
# =========================================================
with st.expander("📊 Queue Log / Export CSV"):
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
        ]

        existing_columns = [col for col in display_columns if col in df.columns]
        df_display = df[existing_columns].copy()

        if "assigned_at" in df_display.columns:
            df_display["assigned_at"] = df_display["assigned_at"].apply(format_datetime)

        if "returned_at" in df_display.columns:
            df_display["returned_at"] = df_display["returned_at"].apply(format_datetime)

        st.dataframe(df_display, use_container_width=True, hide_index=True)

        csv = df.to_csv(index=False).encode("utf-8-sig")

        st.download_button(
            label="Download CSV",
            data=csv,
            file_name="toilet_queue_log.csv",
            mime="text/csv",
        )