import re
from datetime import datetime, timezone

import pandas as pd
import streamlit as st
from theme import apply_ntu_purple_theme
from streamlit_autorefresh import st_autorefresh
import html as html_lib
from typing import Optional, Dict, Any


from core import (
    ToiletQueueCore,
    LOCATIONS,
    STATUS_QUEUED,
    STATUS_IN_PROGRESS,
    STATUS_RETURNED,
    format_datetime,
    get_queue_code,
)

# =========================================================
# STREAMLIT CONFIG
# =========================================================
st.set_page_config(
    page_title="Toilet Queue",
    page_icon="🚻",
    layout="centered",
    initial_sidebar_state="collapsed",
)

apply_ntu_purple_theme()

# =========================================================
# CSS
# =========================================================
st.markdown(
    """
    <style>
    html, body, .stApp {
        width: 100% !important;
        max-width: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow-x: hidden !important;
    }

    [data-testid="stMainBlockContainer"],
    .block-container {
        width: min(100vw, 430px) !important;
        max-width: 430px !important;
        margin-left: auto !important;
        margin-right: auto !important;
        padding-top: 0.25rem !important;
        padding-left: 0.75rem !important;
        padding-right: 0.75rem !important;
        padding-bottom: 1rem !important;
        box-sizing: border-box !important;
        overflow-x: hidden !important;
    }

    #MainMenu,
    footer,
    header,
    [data-testid="stHeader"] {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
    }

    div[data-testid="stButton"] > button {
        min-height: 40px !important;
        border-radius: 14px !important;
        font-size: 0.95rem !important;
        font-weight: 800 !important;
        padding: 0.15rem 0.15rem !important;
        white-space: nowrap !important;
    }

    .app-title {
        font-size: 1rem;
        font-weight: 800;
        margin: 0.3rem 0 0.6rem 0;
    }

    .section-title {
        font-size: 1.45rem;
        font-weight: 900;
        margin: 0.8rem 0 0.45rem 0;
    }

    .small-title {
        font-size: 1.05rem;
        font-weight: 800;
        margin: 0.7rem 0 0.35rem 0;
    }

    .seat-preview {
        width: 100%;
        border: 2px solid #d9d9d9;
        border-radius: 18px;
        text-align: center;
        padding: 0.75rem 0;
        margin: 0.4rem 0 0.75rem 0;
        font-size: 2.1rem;
        font-weight: 900;
        background-color: #fafafa;
        letter-spacing: 0.08rem;
        box-sizing: border-box;
    }

    .preview-box {
        width: 100%;
        text-align: center;
        font-size: 1.05rem;
        font-weight: 800;
        padding: 0.7rem 0;
        border-radius: 14px;
        background-color: #f3f3f3;
        margin: 0.75rem 0;
        box-sizing: border-box;
    }

    .success-note {
        text-align: center;
        font-weight: 800;
        padding: 0.65rem;
        border-radius: 12px;
        background-color: #f4f4f4;
        margin-bottom: 0.6rem;
    }

    .error-note {
        text-align: center;
        font-weight: 800;
        padding: 0.65rem;
        border-radius: 12px;
        background-color: #ffecec;
        color: #b00020;
        margin-bottom: 0.6rem;
    }

    .toilet-status-row {
        display: flex;
        flex-direction: row;
        gap: 0.5rem;
        width: 100%;
        margin: 0.7rem 0 1rem 0;
        box-sizing: border-box;
    }

    .toilet-box {
        flex: 1;
        min-width: 0;
        border: 2px solid #2e7d32;
        border-radius: 16px;
        padding: 0.65rem 0.25rem;
        text-align: center;
        background-color: #f1fff1;
        min-height: 74px;
        box-sizing: border-box;
        overflow: hidden;
    }

    .toilet-box-busy {
        border-color: #d00000;
        background-color: #fff3f3;
    }

    .toilet-title {
        font-size: 0.82rem;
        font-weight: 900;
        margin-bottom: 0.35rem;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .toilet-status {
        font-size: 0.75rem;
        font-weight: 900;
    }

    .toilet-code {
        font-size: 0.9rem;
        font-weight: 900;
        color: #d00000;
        margin-top: 0.1rem;
    }

    .queue-card-top {
        display: grid;
        grid-template-columns: 38% 62%;
        gap: 0.5rem;
        width: 100%;
        box-sizing: border-box;
        align-items: start;
    }

    .queue-code {
        font-size: 1.55rem;
        font-weight: 900;
        line-height: 1.2;
        word-break: break-word;
    }

    .queue-meta {
        font-size: 0.9rem;
        color: #333333;
        line-height: 1.5;
        word-break: break-word;
        overflow-wrap: anywhere;
    }

    .status-inprogress {
        color: #d00000;
        font-weight: 900;
    }

    .call-nudge {
        border: 3px solid #d00000;
        border-radius: 16px;
        padding: 0.45rem;
        animation: nudgePulse 0.35s ease-in-out 0s 10 alternate;
        background-color: #fff5f5;
    }

    .normal-card-content {
        border: 2px solid transparent;
        border-radius: 12px;
        padding: 0.1rem;
    }

    @keyframes nudgePulse {
        0% {
            border-color: #d00000;
            box-shadow: 0 0 0px rgba(208, 0, 0, 0.2);
            transform: translateX(0);
        }
        25% {
            transform: translateX(-3px);
        }
        50% {
            border-color: #ff0000;
            box-shadow: 0 0 14px rgba(208, 0, 0, 0.65);
            transform: translateX(3px);
        }
        100% {
            border-color: #d00000;
            box-shadow: 0 0 4px rgba(208, 0, 0, 0.35);
            transform: translateX(0);
        }
    }


    /* Seat number input box */
    div[data-testid="stNumberInput"] input {
        height: 70px !important;
        font-size: 1.8rem !important;
        font-weight: 800 !important;
        text-align: center !important;
        border: 3px solid #7a005c !important;
        border-radius: 14px !important;
        padding: 0.4rem !important;
    }

    /* Number input outer container */
    div[data-testid="stNumberInput"] {
        margin-top: 0.3rem !important;
        margin-bottom: 0.5rem !important;
    }

    div[data-testid="stNumberInput"] button {
        display: none !important;
    }   

    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# PASSWORD + SUPABASE
# =========================================================


try:
    APP_PASSWORD = st.secrets["APP_PASSWORD"]
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except KeyError as e:
    st.error(f"Missing Streamlit secret: {e}")
    st.stop()

# Uncomment if you want password screen again.
# password = st.text_input("Event Password", type="password", label_visibility="collapsed")
# if password != APP_PASSWORD:
#     st.warning("Enter password to continue.")
#     st.stop()

core = ToiletQueueCore(SUPABASE_URL, SUPABASE_KEY)

# SESSION STATE
# =========================================================
if "selected_gender" not in st.session_state:
    st.session_state.selected_gender = "Male"

if "seat_no_input" not in st.session_state:
    st.session_state.seat_no_input = ""

if "last_action_message" not in st.session_state:
    st.session_state.last_action_message = ""

if "last_action_ok" not in st.session_state:
    st.session_state.last_action_ok = True


# =========================================================
# HELPERS / CALLBACKS
# =========================================================
def clean_seat(value):
    return re.sub(r"\D", "", str(value or ""))[:4]


def set_message(ok, message):
    st.session_state.last_action_ok = ok
    st.session_state.last_action_message = message


def is_recent_call(called_at_raw, seconds=6):
    if not called_at_raw:
        return False

    try:
        called_at = datetime.fromisoformat(
            str(called_at_raw).replace("Z", "+00:00")
        )
        now = datetime.now(timezone.utc)
        return (now - called_at).total_seconds() <= seconds
    except Exception:
        return False


def select_gender(gender):
    st.session_state.selected_gender = gender


def add_student_callback():
    try:
        seat_value = st.session_state.get("seat_no_number")
        seat_no = "" if seat_value is None else str(int(seat_value))

        ok, message = core.add_student(
            seat_no=seat_no,
            gender=st.session_state.selected_gender,
            queue_event=st.session_state.active_event,
        )

        set_message(ok, message)

        if ok:
            st.session_state.seat_no_number = None

    except Exception as e:
        set_message(False, f"Failed to add student: {e}")

def assign_toilet_callback(row_id, queue_code, gender, toilet):
    try:
        ok, message = core.assign_toilet(
            row_id=row_id,
            queue_code=queue_code,
            gender=gender,
            toilet=toilet,
        )

        if ok:
            call_ok, call_message = core.call_student(row_id, queue_code)

            if call_ok:
                set_message(True, f"{message} {call_message}")
            else:
                set_message(False, call_message)
        else:
            set_message(False, message)

    except Exception as e:
        set_message(False, f"Failed to assign toilet: {e}")


def return_callback(row_id, queue_code):
    try:
        ok, message = core.mark_returned(row_id, queue_code)
        set_message(ok, message)

    except Exception as e:
        set_message(False, f"Failed to mark returned: {e}")


def call_callback(row_id, queue_code):
    try:
        ok, message = core.call_student(row_id, queue_code)
        set_message(ok, message)

    except Exception as e:
        set_message(False, f"Failed to nudge student: {e}")


def move_up_callback(row_id):
    try:
        ok, message = core.move_up(
            row_id,
            queue_event=st.session_state.active_event,
        )
        set_message(ok, message)

    except Exception as e:
        set_message(False, f"Failed to move up: {e}")


def move_down_callback(row_id):
    try:
        ok, message = core.move_down(
            row_id,
            queue_event=st.session_state.active_event,
        )
        set_message(ok, message)

    except Exception as e:
        set_message(False, f"Failed to move down: {e}")


def render_toilet_status_boxes(all_queue):

    toilet_status: Dict[str, Optional[Dict[str, Any]]] = {
        "Male": None,
        "Female": None,
        "Handicap": None,
    }

    for row in all_queue:
        if row.get("status") == STATUS_IN_PROGRESS:
            location = row.get("location")

            if location in toilet_status:
                toilet_status[location] = {
                    "queue_code": row.get("queue_code", ""),
                    "called_at": row.get("called_at"),
                }

    html_parts = ["<div class='toilet-status-row'>"]

    toilet_labels = {
        "Male": "🚹 Male",
        "Female": "🚺 Female",
        "Handicap": "♿ Handicap",
    }

    for toilet in LOCATIONS:
        current = toilet_status.get(toilet)
        toilet_label = toilet_labels.get(toilet, toilet)

        if current:
            queue_code = current.get("queue_code", "")
            called_at = current.get("called_at")
            animation_style = (
                " style='animation:nudgePulse 0.35s ease-in-out 0s 8 alternate;'"
                if is_recent_call(called_at, seconds=6)
                else ""
            )

            html_parts.append(
                f"<div class='toilet-box toilet-box-busy'{animation_style}>"
                f"<div class='toilet-title'>{toilet_label}</div>"
                f"<div class='toilet-status' style='color:#d00000;'>IN USE</div>"
                f"<div class='toilet-code'>{queue_code}</div>"
                f"</div>"
            )
        else:
            html_parts.append(
                f"<div class='toilet-box'>"
                f"<div class='toilet-title'>{toilet_label}</div>"
                f"<div class='toilet-status' style='color:#2e7d32;'>Available</div>"
                f"</div>"
            )

    html_parts.append("</div>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)


def render_queue_card(index, row):
    row_id = row.get("id")
    queue_code = row.get("queue_code", "")
    status = row.get("status", STATUS_QUEUED)
    gender = row.get("gender", "-")
    location = row.get("location", "Unassigned")

    toilet_label = {
        "Unassigned": "Not assigned",
        "Male": "🚹 Male",
        "Female": "🚺 Female",
        "Handicap": "♿ Handicap",
    }.get(location, location)

    assigned_at = format_datetime(row.get("assigned_at"))
    returned_at = format_datetime(row.get("returned_at"))

    called_at = row.get("called_at")
    content_class = "call-nudge" if is_recent_call(called_at, seconds=6) else "normal-card-content"

    code_display = f"✅ {queue_code}" if status == STATUS_RETURNED else f"{index}. {queue_code}"

    if status == STATUS_IN_PROGRESS:
        status_display = "<span class='status-inprogress'>IN PROGRESS</span>"
    else:
        status_display = status

    returned_html = ""
    if status == STATUS_RETURNED:
        returned_html = f"<b>Returned:</b> {returned_at}<br>"

    st.markdown(
        (
            f"<div class='{content_class}'>"
            f"<div class='queue-card-top'>"
            f"<div class='queue-code'>{code_display}</div>"
            f"<div class='queue-meta'>"
            f"<b>Status:</b> {status_display}<br>"
            f"<b>Toilet:</b> {toilet_label}<br>"
            f"<b>Assigned:</b> {assigned_at}<br>"
            f"{returned_html}"
            f"</div>"
            f"</div>"
            f"</div>"
        ),
        unsafe_allow_html=True,
    )

    if status == STATUS_QUEUED:

        st.markdown("<div class='small-title'>Assign Toilet</div>", unsafe_allow_html=True)

        assign_cols = st.columns(3)

        with assign_cols[0]:
            st.button(
                "🚹 Male",
                key=f"assign_male_{row_id}",
                on_click=assign_toilet_callback,
                args=(row_id, queue_code, gender, "Male"),
                use_container_width=True,
            )

        with assign_cols[1]:
            st.button(
                "🚺 Female",
                key=f"assign_female_{row_id}",
                on_click=assign_toilet_callback,
                args=(row_id, queue_code, gender, "Female"),
                use_container_width=True,
            )

        with assign_cols[2]:
            st.button(
                "♿ Handicap",
                key=f"assign_handicap_{row_id}",
                on_click=assign_toilet_callback,
                args=(row_id, queue_code, gender, "Handicap"),
                use_container_width=True,
            )

            arrow_cols = st.columns(2, gap="small")

            with arrow_cols[0]:
                st.button(
                    "⬆️",
                    key=f"up_{row_id}",
                    on_click=move_up_callback,
                    args=(row_id,),
                    use_container_width=True,
                )

            with arrow_cols[1]:
                st.button(
                    "⬇️",
                    key=f"down_{row_id}",
                    on_click=move_down_callback,
                    args=(row_id,),
                    use_container_width=True,
                )

    elif status == STATUS_IN_PROGRESS:
        action_cols = st.columns(2, gap="small")

        with action_cols[0]:
            st.button(
                "📣 Nudge",
                key=f"nudge_{row_id}",
                on_click=call_callback,
                args=(row_id, queue_code),
                use_container_width=True,
            )

        with action_cols[1]:
            st.button(
                "✅ Return",
                key=f"return_{row_id}",
                type="primary",
                on_click=return_callback,
                args=(row_id, queue_code),
                use_container_width=True,
            )

    elif status == STATUS_RETURNED:
        st.caption("Returned — will hide after 10 seconds.")

def render_in_queue_summary(all_queue):
    male_count = sum(
        1 for row in all_queue
        if row.get("status") == STATUS_QUEUED and row.get("gender") == "Male"
    )

    female_count = sum(
        1 for row in all_queue
        if row.get("status") == STATUS_QUEUED and row.get("gender") == "Female"
    )

    male_color = "#d00000" if male_count >= 5 else "#222222"
    female_color = "#d00000" if female_count >= 5 else "#222222"

    st.markdown(
        f"""
        <div style="
            width:100%;
            background:#f3f3f3;
            border-radius:14px;
            padding:0.25rem;
            margin:0.2rem 0 0.2rem 0;
            text-align:left;
            box-sizing:border-box;
            line-height:1;
        ">
            <div style="font-size:1rem;">
                <span style="color:{male_color};">Male: <span style="font-weight:900;">{male_count}</span></span>
                <span style="color:#777;"> | </span>
                <span style="color:{female_color};">Female: <span style="font-weight:900;">{female_count}</span></span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# =========================================================
# EVENT MANAGEMENT UI
# =========================================================
def render_event_manager():
    try:
        events = core.list_events()
        active_event = core.get_active_event()
    except Exception as e:
        st.error(f"Failed to load events: {e}")
        return "default"

    event_names = [row.get("event_name") for row in events if row.get("event_name")]

    if not event_names:
        event_names = ["default"]

    if "pending_event_switch" not in st.session_state:
        st.session_state.pending_event_switch = None

    # Show active event at the top of the page
    st.markdown(
        f"""
        <div style="
            width:100%;
            background:#ffffff;
            border-radius:14px;
            padding:0.45rem;
            margin:0.2rem 0 0.6rem 0;
            box-sizing:border-box;
            text-align:center;
            font-weight:700;
        ">
            Active Event:
            <span style="font-weight:900; color:#70005d;">{active_event}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("➕ Create / Switch Event"):
        selected_event = st.selectbox(
            "Select Event",
            event_names,
            index=event_names.index(active_event) if active_event in event_names else 0,
            key="event_selector",
        )

        if selected_event != active_event:
            st.session_state.pending_event_switch = selected_event

        if st.session_state.pending_event_switch:
            pending = st.session_state.pending_event_switch

            st.warning(f"Switch to {pending}? This will affect all users.")

            confirm_cols = st.columns(2)

            with confirm_cols[0]:
                if st.button(
                    "OK",
                    key="confirm_event_switch",
                    type="primary",
                    use_container_width=True,
                ):
                    try:
                        ok, message = core.set_active_event(pending)
                        set_message(ok, message)
                        st.session_state.pending_event_switch = None
                        st.rerun()
                    except Exception as e:
                        set_message(False, f"Failed to switch event: {e}")

            with confirm_cols[1]:
                if st.button(
                    "Cancel",
                    key="cancel_event_switch",
                    use_container_width=True,
                ):
                    st.session_state.pending_event_switch = None
                    st.rerun()

        st.markdown("---")

        new_event_name = st.text_input(
            "New Event Name",
            placeholder="e.g. Y3_OSCE_AM",
            key="new_event_name",
        )

        if st.button("Create Event", key="create_event", use_container_width=True):
            try:
                cleaned_event_name = new_event_name.strip()

                ok, message = core.create_event(cleaned_event_name)
                set_message(ok, message)

                if ok:
                    st.rerun()

            except Exception as e:
                set_message(False, f"Failed to create event: {e}")

    return active_event

# =========================================================
# AUTO REFRESH + ARCHIVE
# =========================================================
st_autorefresh(interval=3000, key="queue_autorefresh")

try:
    core.archive_old_returned(seconds=10)
except Exception as e:
    st.warning(f"Archive skipped: {e}")


# =========================================================
# ADD STUDENT SECTION
# =========================================================
st.markdown("<div class='app-title'>🚻 Toilet Queue</div>", unsafe_allow_html=True)

active_event = render_event_manager()
st.session_state.active_event = active_event

st.markdown("<div class='section-title'>Gender</div>", unsafe_allow_html=True)

gender_cols = st.columns(2, gap="small")

with gender_cols[0]:
    st.button(
        "Male ♂️",
        key="gender_male",
        type="primary" if st.session_state.selected_gender == "Male" else "secondary",
        on_click=select_gender,
        args=("Male",),
        use_container_width=True,
    )

with gender_cols[1]:
    st.button(
        "Female ♀️",
        key="gender_female",
        type="primary" if st.session_state.selected_gender == "Female" else "secondary",
        on_click=select_gender,
        args=("Female",),
        use_container_width=True,
    )

st.markdown("<div class='small-title'>➕ Add Student</div>", unsafe_allow_html=True)

seat_value = st.number_input(
    "Seat Number",
    min_value=0,
    max_value=999,
    step=1,
    value=None,
    placeholder="Enter seat number",
    key="seat_no_number",
)

seat_clean = "" if seat_value is None else str(int(seat_value))

seat_display = seat_clean or "—"

preview_code = (
    get_queue_code(seat_clean, st.session_state.selected_gender)
    if seat_clean
    else "-"
)

st.markdown(
    f"<div class='seat-preview'>{preview_code}</div>",
    unsafe_allow_html=True,
)

# st.markdown(
#     f"<div class='preview-box'>Queue Code: {preview_code}</div>",
#     unsafe_allow_html=True,
# )

st.button(
    "➕ Add to Queue",
    key="add_to_queue",
    type="primary",
    on_click=add_student_callback,
    use_container_width=True,
)

if st.session_state.last_action_message:
    note_class = "success-note" if st.session_state.last_action_ok else "error-note"
    st.markdown(
        f"<div class='{note_class}'>{st.session_state.last_action_message}</div>",
        unsafe_allow_html=True,
    )



# =========================================================
# ACTIVE QUEUE SECTION
# =========================================================
try:
    all_queue = core.load_active_queue(st.session_state.active_event)
except Exception as e:
    st.error(f"Failed to load active queue: {e}")
    all_queue = []

all_queue = sorted(
    all_queue,
    key=lambda x: (
        0 if x.get("status") == STATUS_IN_PROGRESS else
        1 if x.get("status") == STATUS_QUEUED else
        2,
        x.get("queue_order", 9999) or 9999,
        x.get("created_at", ""),
    )
)

st.markdown(
    "<div class='section-title'>⏱️ In Queue</div>",
    unsafe_allow_html=True,
)

render_in_queue_summary(all_queue)

st.markdown(
    "<div class='section-title'>📋 Active Queue</div>",
    unsafe_allow_html=True,
)

render_toilet_status_boxes(all_queue)

if not all_queue:
    st.info("No active queue.")
else:
    for index, row in enumerate(all_queue, start=1):
        with st.container(border=True):
            render_queue_card(index, row)

# active_event = render_event_manager()
# st.session_state.active_event = active_event

# =========================================================
# LOG SECTION
# =========================================================
with st.expander("📊 Queue Log / Export CSV"):
    try:
        log_rows = core.load_log(st.session_state.active_event)
    except Exception as e:
        st.error(f"Failed to load queue log: {e}")
        log_rows = []

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
            "called_at",
            "created_at",
        ]

        existing_columns = [col for col in display_columns if col in df.columns]
        df_display = df[existing_columns].copy()

        if "assigned_at" in df_display.columns:
            df_display["assigned_at"] = df_display["assigned_at"].apply(format_datetime)

        if "returned_at" in df_display.columns:
            df_display["returned_at"] = df_display["returned_at"].apply(format_datetime)

        st.dataframe(df_display, use_container_width=True, hide_index=True)

        csv = df.to_csv(index=False).encode("utf-8-sig")

        safe_event_name = st.session_state.active_event.replace(" ", "_").replace("/", "_")

        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"toilet_queue_log_{safe_event_name}.csv",
            mime="text/csv",
            use_container_width=True,
        )

st.space(size="large")
st.space(size="large")