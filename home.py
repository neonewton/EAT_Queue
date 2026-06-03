import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, timezone

from core import (
    ToiletQueueCore,
    GENDERS,
    LOCATIONS,
    TOILET_LABELS,
    STATUS_QUEUED,
    STATUS_IN_PROGRESS,
    STATUS_RETURNED,
    format_datetime,
    get_queue_code,
    SGT,
)

try:
    from theme import apply_ntu_purple_theme
except Exception:
    apply_ntu_purple_theme = None


# =========================================================
# STREAMLIT CONFIG
# =========================================================
st.set_page_config(
    page_title="Toilet Queue",
    page_icon="🚻",
    layout="centered",
    initial_sidebar_state="collapsed",
)

if apply_ntu_purple_theme:
    apply_ntu_purple_theme()


# =========================================================
# MOBILE-FIRST CSS
# =========================================================
st.markdown(
    """
    <style>
    .block-container {
        max-width: 430px !important;
        padding-top: 0.55rem !important;
        padding-left: 0.75rem !important;
        padding-right: 0.75rem !important;
        padding-bottom: 1rem !important;
    }

    h1 {
        text-align: center !important;
        font-size: 1.45rem !important;
        margin-bottom: 0.1rem !important;
    }

    h2, h3 {
        margin-top: 0.1rem !important;
        margin-bottom: 0.1rem !important;
    }

    div[data-testid="stHorizontalBlock"] {
        gap: 0.1rem !important;
    }

    div[data-testid="column"] {
        min-width: 0 !important;
    }

    div[data-testid="stButton"] > button {
        width: 100% !important;
        min-height: 54px !important;
        border-radius: 14px !important;
        font-size: 0.98rem !important;
        font-weight: 800 !important;
        padding: 0.4rem 0.15rem !important;
        white-space: nowrap !important;
    }

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

    .queue-code {
        font-size: 1.8rem;
        font-weight: 900;
        margin-bottom: 0.35rem;
    }

    .queue-meta {
        font-size: 0.92rem;
        color: #555;
        line-height: 1.55;
        margin-bottom: 0.75rem;
    }

    .status-inprogress {
        color: #d00000;
        font-weight: 900;
        font-size: 1rem;
    }

    .assign-title {
        font-size: 0.95rem;
        font-weight: 900;
        margin-top: 0.35rem;
        margin-bottom: 0.35rem;
    }

    .call-nudge {
        border: 3px solid #d00000;
        border-radius: 18px;
        padding: 0.75rem;
        animation: nudgePulse 0.35s ease-in-out 0s 8 alternate;
        background-color: #fff5f5;
    }

    .normal-card-content {
        border: 2px solid transparent;
        border-radius: 18px;
        padding: 0.75rem;
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

        .toilet-status-row {
            display: flex;
            gap: 0.5rem;
            width: 100%;
            margin: 0.75rem 0 1rem 0;
        }

        .toilet-box {
            flex: 1;
            border: 2px solid #dddddd;
            border-radius: 16px;
            padding: 0.75rem 0.35rem;
            text-align: center;
            background-color: #ffffff;
            min-height: 88px;
        }

        .toilet-box-free {
            border-color: #2e7d32;
            background-color: #f1fff1;
        }

        .toilet-box-busy {
            border-color: #d00000;
            background-color: #fff3f3;
            animation: toiletPulse 0.9s ease-in-out infinite alternate;
        }

        .toilet-title {
            font-size: 0.9rem;
            font-weight: 900;
            margin-bottom: 0.3rem;
        }

        .toilet-status {
            font-size: 0.8rem;
            font-weight: 800;
        }

        .toilet-code {
            font-size: 1rem;
            font-weight: 900;
            color: #d00000;
        }

        @keyframes toiletPulse {
            from {
                box-shadow: 0 0 0 rgba(208, 0, 0, 0.15);
            }
            to {
                box-shadow: 0 0 12px rgba(208, 0, 0, 0.35);
            }
        }
        
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
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


# =========================================================
# SESSION STATE
# =========================================================
if "seat_no_text" not in st.session_state:
    st.session_state.seat_no_text = ""

if "selected_gender" not in st.session_state:
    st.session_state.selected_gender = "Male"

if "last_action_message" not in st.session_state:
    st.session_state.last_action_message = ""

if "last_action_ok" not in st.session_state:
    st.session_state.last_action_ok = True


# =========================================================
# CALLBACKS
# =========================================================
def set_message(ok, message):
    st.session_state.last_action_ok = ok
    st.session_state.last_action_message = message


def append_digit(digit):
    if len(st.session_state.seat_no_text) < 4:
        st.session_state.seat_no_text += str(digit)


def backspace_digit():
    st.session_state.seat_no_text = st.session_state.seat_no_text[:-1]


def clear_digits():
    st.session_state.seat_no_text = ""


def select_gender(gender):
    st.session_state.selected_gender = gender


def add_student_callback():
    try:
        ok, message = core.add_student(
            seat_no=st.session_state.seat_no_text,
            gender=st.session_state.selected_gender,
        )

        set_message(ok, message)

        if ok:
            st.session_state.seat_no_text = ""

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

        # If assignment is successful, immediately trigger Call/Nudge
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


def move_up_callback(row_id):
    try:
        ok, message = core.move_up(row_id)
        set_message(ok, message)

    except Exception as e:
        set_message(False, f"Failed to move up: {e}")


def move_down_callback(row_id):
    try:
        ok, message = core.move_down(row_id)
        set_message(ok, message)

    except Exception as e:
        set_message(False, f"Failed to move down: {e}")


def is_recent_call(called_at_raw, seconds=3):
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
    
def call_callback(row_id, queue_code):
    try:
        ok, message = core.call_student(row_id, queue_code)
        set_message(ok, message)

    except Exception as e:
        set_message(False, f"Failed to call student: {e}")

def render_toilet_status_boxes(all_queue):
    toilet_status = {
        "Male": None,
        "Female": None,
        "Handicap": None,
    }

    for row in all_queue:
        if row.get("status") == STATUS_IN_PROGRESS:
            location = row.get("location")
            if location in toilet_status:
                toilet_status[location] = row.get("queue_code", "")

    html_parts = [
        "<div style='display:flex; flex-direction:row; gap:8px; width:100%; margin:10px 0 16px 0;'>"
    ]

    for toilet in LOCATIONS:
        queue_code = toilet_status.get(toilet)
        toilet_label = TOILET_LABELS.get(toilet, toilet)

        if queue_code:
            border_color = "#d00000"
            bg_color = "#fff3f3"
            status_html = (
                "<div style='font-size:0.75rem; font-weight:800; color:#d00000;'>IN USE</div>"
                f"<div style='font-size:0.95rem; font-weight:900; color:#d00000;'>{queue_code}</div>"
            )
        else:
            border_color = "#2e7d32"
            bg_color = "#f1fff1"
            status_html = (
                "<div style='font-size:0.75rem; font-weight:800; color:#2e7d32;'>Available</div>"
            )

        html_parts.append(
            f"<div style='flex:1; min-width:0; border:2px solid {border_color}; "
            f"border-radius:14px; background:{bg_color}; padding:10px 4px; "
            f"text-align:center; min-height:76px;'>"
            f"<div style='font-size:0.8rem; font-weight:900; margin-bottom:6px;'>{toilet_label}</div>"
            f"{status_html}"
            f"</div>"
        )

    html_parts.append("</div>")

    st.markdown("".join(html_parts), unsafe_allow_html=True)

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
st.markdown("🚻 Toilet Queue")

st.markdown("### Gender")

gender_cols = st.columns(2)

with gender_cols[0]:
    st.button(
        "Male♂️",
        key="gender_male",
        type="primary" if st.session_state.selected_gender == "Male" else "secondary",
        on_click=select_gender,
        args=("Male",),
        use_container_width=True,
    )

with gender_cols[1]:
    st.button(
        "Female♀️",
        key="gender_female",
        type="primary" if st.session_state.selected_gender == "Female" else "secondary",
        on_click=select_gender,
        args=("Female",),
        use_container_width=True,
    )

st.markdown("➕ Add Student")

seat_display = st.session_state.seat_no_text or "—"

st.markdown(
    f"<div class='seat-display'>{seat_display}</div>",
    unsafe_allow_html=True,
)

pad_rows = [
    ["1", "2", "3"],
    ["4", "5", "6"],
    ["7", "8", "9"],
    ["C", "0", "⌫"],
]

# Keypad - fixed width, centred
keypad_left, keypad_mid, keypad_right = st.columns([0.12, 0.76, 0.12])

with keypad_mid:
    for row_index, row in enumerate(pad_rows):
        cols = st.columns(3, gap="small")

        for col, key in zip(cols, row):
            with col:
                if key == "C":
                    st.button(
                        "C",
                        key=f"pad_clear_{row_index}",
                        on_click=clear_digits,
                        use_container_width=True,
                    )
                elif key == "⌫":
                    st.button(
                        "⌫",
                        key=f"pad_backspace_{row_index}",
                        on_click=backspace_digit,
                        use_container_width=True,
                    )
                else:
                    st.button(
                        key,
                        key=f"pad_{key}_{row_index}",
                        on_click=append_digit,
                        args=(key,),
                        use_container_width=True,
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
# =========================================================
# ACTIVE QUEUE SECTION
# =========================================================
st.subheader("📋 Active Queue")

try:
    all_queue = core.load_active_queue()
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

render_toilet_status_boxes(all_queue)

if not all_queue:
    st.info("No active queue.")
else:
    for index, row in enumerate(all_queue, start=1):
        row_id = row.get("id")
        queue_code = row.get("queue_code", "")
        seat = row.get("seat_no", "")
        status = row.get("status", STATUS_QUEUED)
        gender = row.get("gender", "-")
        location = row.get("location", "Unassigned")
        toilet_label = TOILET_LABELS.get(location, location)

        assigned_at = format_datetime(row.get("assigned_at"))
        returned_at = format_datetime(row.get("returned_at"))

        called_at = row.get("called_at")
        is_called_recently = is_recent_call(called_at, seconds=6)
        content_class = "call-nudge" if is_called_recently else "normal-card-content"

        with st.container(border=True):
            if status == STATUS_RETURNED:
                code_display = f"✅ {queue_code}"
            else:
                code_display = f"{index}. {queue_code}"

            if status == STATUS_IN_PROGRESS:
                status_display = "<span class='status-inprogress'>IN PROGRESS</span>"
            else:
                status_display = status

            st.markdown(
                f"""
                <div class="{content_class}">
                    <div class="queue-code">{code_display}</div>
                    <div class="queue-meta">
                        <b>Seat:</b> {seat}<br>
                        <b>Status:</b> {status_display}<br>
                        <b>Gender:</b> {gender}<br>
                        <b>Toilet:</b> {toilet_label}<br>
                        <b>Assigned:</b> {assigned_at}<br>
                        <b>Returned:</b> {returned_at}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if status == STATUS_QUEUED:
                st.markdown(
                    "<div class='assign-title'>Assign Toilet</div>",
                    unsafe_allow_html=True,
                )

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

                move_cols = st.columns(2)

                with move_cols[0]:
                    st.button(
                        "⬆️ Move Up",
                        key=f"up_{row_id}",
                        on_click=move_up_callback,
                        args=(row_id,),
                        use_container_width=True,
                    )

                with move_cols[1]:
                    st.button(
                        "⬇️ Move Down",
                        key=f"down_{row_id}",
                        on_click=move_down_callback,
                        args=(row_id,),
                        use_container_width=True,
                    )

            elif status == STATUS_IN_PROGRESS:
                action_cols = st.columns(2)

                with action_cols[0]:
                    st.button(
                        "📣 Nudge",
                        key=f"call_{row_id}",
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


# =========================================================
# LOG SECTION
# =========================================================
with st.expander("📊 Queue Log / Export CSV"):
    try:
        log_rows = core.load_log()
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

        st.dataframe(df_display, use_container_width=True, hide_index=False)

        csv = df.to_csv(index=False).encode("utf-8-sig")

        st.download_button(
            label="Download CSV",
            data=csv,
            file_name="toilet_queue_log.csv",
            mime="text/csv",
            use_container_width=True,
        )