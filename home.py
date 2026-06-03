import html as html_lib
from datetime import datetime, timezone
from urllib.parse import urlencode

import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from core import (
    ToiletQueueCore,
    LOCATIONS,
    STATUS_QUEUED,
    STATUS_IN_PROGRESS,
    STATUS_RETURNED,
    format_datetime,
    get_queue_code,
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
# CSS
# =========================================================
st.markdown(
    """
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">

    <style>
    html, body, .stApp {
        width: 100% !important;
        max-width: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow-x: hidden !important;
    }

    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    section.main,
    .main {
        width: 100% !important;
        max-width: 100% !important;
        margin: 0 auto !important;
        padding: 0 !important;
        display: block !important;
        overflow-x: hidden !important;
    }

    [data-testid="stMainBlockContainer"],
    .block-container {
        width: min(100vw, 430px) !important;
        max-width: 430px !important;
        margin-left: auto !important;
        margin-right: auto !important;
        padding-top: 0.1rem !important;
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

    h1, h2, h3 {
        margin-top: 0.15rem !important;
        margin-bottom: 0.15rem !important;
    }

    div[data-testid="stButton"] > button {
        min-height: 46px !important;
        border-radius: 14px !important;
        font-size: 0.95rem !important;
        font-weight: 800 !important;
        padding: 0.35rem 0.4rem !important;
        white-space: nowrap !important;
    }

    .app-title {
        font-size: 1rem;
        font-weight: 800;
        margin: 0.2rem 0 0.5rem 0;
    }

    .section-title {
        font-size: 1.55rem;
        font-weight: 900;
        margin: 0.7rem 0 0.45rem 0;
    }

    .small-title {
        font-size: 1.05rem;
        font-weight: 800;
        margin: 0.55rem 0 0.35rem 0;
    }

    .seat-display {
        width: 100%;
        border: 2px solid #d9d9d9;
        border-radius: 18px;
        text-align: center;
        padding: 0.75rem 0;
        margin: 0.35rem 0 0.7rem 0;
        font-size: 2.3rem;
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

    .html-button {
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 44px;
        border: 1.5px solid #7a005c;
        border-radius: 14px;
        background: #ffffff;
        color: #7a005c;
        font-weight: 800;
        font-size: 0.95rem;
        text-decoration: none !important;
        box-sizing: border-box;
        padding: 0.35rem 0.35rem;
        white-space: nowrap;
        overflow: hidden;
    }

    .html-button-primary {
        background: #70005d;
        color: #ffffff !important;
        border-color: #70005d;
    }

    .html-button-secondary {
        background: #ffffff;
        color: #70005d !important;
        border-color: #70005d;
    }

    .gender-row,
    .numpad-row,
    .toilet-status-row,
    .assign-row,
    .action-row,
    .arrow-row {
        display: flex;
        flex-direction: row;
        width: 100%;
        box-sizing: border-box;
    }

    .gender-row {
        gap: 0.5rem;
        margin: 0.45rem 0 0.75rem 0;
    }

    .gender-row .html-button {
        flex: 1;
    }

    .numpad-wrap {
        width: 100%;
        max-width: 320px;
        margin: 0 auto 0.8rem auto;
        box-sizing: border-box;
    }

    .numpad-row {
        gap: 0.45rem;
        margin-bottom: 0.45rem;
    }

    .numpad-row .html-button {
        flex: 1;
        height: 46px;
        min-height: 46px;
    }

    .toilet-status-row {
        gap: 0.55rem;
        margin: 0.7rem 0 1rem 0;
    }

    .toilet-box {
        flex: 1;
        min-width: 0;
        border: 2px solid #2e7d32;
        border-radius: 16px;
        padding: 0.65rem 0.25rem;
        text-align: center;
        background-color: #f1fff1;
        min-height: 76px;
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

    .queue-top {
        display: flex;
        flex-direction: row;
        align-items: flex-start;
        gap: 0.6rem;
        width: 100%;
        box-sizing: border-box;
    }

    .queue-left {
        flex: 0 0 38%;
        min-width: 0;
    }

    .queue-right {
        flex: 1;
        min-width: 0;
    }

    .queue-code {
        font-size: 1.45rem;
        font-weight: 900;
        line-height: 1.2;
        word-break: break-word;
    }

    .queue-meta {
        font-size: 0.92rem;
        color: #333333;
        line-height: 1.55;
        word-break: break-word;
        overflow-wrap: anywhere;
    }

    .status-inprogress {
        color: #d00000;
        font-weight: 900;
    }

    .normal-card-content {
        border: 2px solid transparent;
        border-radius: 12px;
        padding: 0.15rem;
    }

    .call-nudge {
        border: 3px solid #d00000;
        border-radius: 16px;
        padding: 0.45rem;
        animation: nudgePulse 0.35s ease-in-out 0s 10 alternate;
        background-color: #fff5f5;
    }

    .arrow-row {
        gap: 0.4rem;
        margin-top: 0.45rem;
        max-width: 110px;
        margin-left: auto;
    }

    .arrow-row .html-button {
        flex: 1;
        height: 38px;
        min-height: 38px;
        font-size: 0.85rem;
        padding: 0.15rem;
    }

    .assign-title {
        font-size: 0.95rem;
        font-weight: 900;
        margin: 0.7rem 0 0.35rem 0;
    }

    .assign-row {
        gap: 0.35rem;
    }

    .assign-row .html-button {
        flex: 1;
        font-size: 0.85rem;
        min-height: 42px;
    }

    .action-row {
        gap: 0.45rem;
        margin-top: 0.7rem;
    }

    .action-row .html-button {
        flex: 1;
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
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# SUPABASE
# =========================================================
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except KeyError as e:
    st.error(f"Missing Streamlit secret: {e}")
    st.stop()

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
# HELPERS
# =========================================================
def make_url(params):
    return "?" + urlencode(params)


def set_message(ok, message):
    st.session_state.last_action_ok = ok
    st.session_state.last_action_message = message


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


def find_active_row(row_id):
    try:
        target_id = int(row_id)
    except Exception:
        target_id = row_id

    rows = core.load_active_queue()

    for row in rows:
        if row.get("id") == target_id:
            return row

    return None


def handle_query_actions():
    gender_value = st.query_params.get("gender")
    pad_value = st.query_params.get("pad")
    action = st.query_params.get("action")
    row_id = st.query_params.get("id")

    if gender_value:
        if gender_value in ["Male", "Female"]:
            st.session_state.selected_gender = gender_value

        st.query_params.clear()
        st.rerun()

    if pad_value:
        if pad_value == "C":
            st.session_state.seat_no_text = ""
        elif pad_value == "BACK":
            st.session_state.seat_no_text = st.session_state.seat_no_text[:-1]
        elif pad_value.isdigit():
            if len(st.session_state.seat_no_text) < 4:
                st.session_state.seat_no_text += pad_value

        st.query_params.clear()
        st.rerun()

    if action and row_id:
        row = find_active_row(row_id)

        if not row:
            set_message(False, "Selected queue item is no longer active.")
            st.query_params.clear()
            st.rerun()

        try:
            target_id = int(row_id)
        except Exception:
            target_id = row_id

        queue_code = row.get("queue_code", "")
        gender = row.get("gender", "")

        try:
            if action == "assign":
                toilet = st.query_params.get("toilet")

                ok, message = core.assign_toilet(
                    row_id=target_id,
                    queue_code=queue_code,
                    gender=gender,
                    toilet=toilet,
                )

                if ok:
                    call_ok, call_message = core.call_student(target_id, queue_code)

                    if call_ok:
                        set_message(True, f"{message} {call_message}")
                    else:
                        set_message(False, call_message)
                else:
                    set_message(False, message)

            elif action == "return":
                ok, message = core.mark_returned(target_id, queue_code)
                set_message(ok, message)

            elif action == "nudge":
                ok, message = core.call_student(target_id, queue_code)
                set_message(ok, message)

            elif action == "up":
                ok, message = core.move_up(target_id)
                set_message(ok, message)

            elif action == "down":
                ok, message = core.move_down(target_id)
                set_message(ok, message)

        except Exception as e:
            set_message(False, f"Action failed: {e}")

        st.query_params.clear()
        st.rerun()


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


def render_link_button(label, params, primary=False):
    safe_label = html_lib.escape(label)
    css_class = "html-button html-button-primary" if primary else "html-button html-button-secondary"
    return f"<a class='{css_class}' href='{make_url(params)}'>{safe_label}</a>"


def render_gender_selector():
    male_primary = st.session_state.selected_gender == "Male"
    female_primary = st.session_state.selected_gender == "Female"

    html = (
        "<div class='gender-row'>"
        + render_link_button("Male ♂️", {"gender": "Male"}, primary=male_primary)
        + render_link_button("Female ♀️", {"gender": "Female"}, primary=female_primary)
        + "</div>"
    )

    st.markdown(html, unsafe_allow_html=True)


def render_html_numpad():
    pad_rows = [
        ["1", "2", "3"],
        ["4", "5", "6"],
        ["7", "8", "9"],
        ["C", "0", "BACK"],
    ]

    html_parts = ["<div class='numpad-wrap'>"]

    for row in pad_rows:
        html_parts.append("<div class='numpad-row'>")

        for key in row:
            label = "⌫" if key == "BACK" else key
            html_parts.append(
                render_link_button(label, {"pad": key}, primary=False)
            )

        html_parts.append("</div>")

    html_parts.append("</div>")

    st.markdown("".join(html_parts), unsafe_allow_html=True)


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
            queue_code = html_lib.escape(current.get("queue_code", ""))
            called_at = current.get("called_at")
            is_called_recently = is_recent_call(called_at, seconds=6)

            animation_style = (
                " style='animation:nudgePulse 0.35s ease-in-out 0s 8 alternate;'"
                if is_called_recently
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
    is_called_recently = is_recent_call(called_at, seconds=6)
    content_class = "call-nudge" if is_called_recently else "normal-card-content"

    if status == STATUS_RETURNED:
        code_display = f"✅ {queue_code}"
    else:
        code_display = f"{index}. {queue_code}"

    if status == STATUS_IN_PROGRESS:
        status_display = "<span class='status-inprogress'>IN PROGRESS</span>"
    else:
        status_display = html_lib.escape(status)

    returned_html = ""
    if status == STATUS_RETURNED:
        returned_html = f"<b>Returned:</b> {html_lib.escape(returned_at)}<br>"

    arrows_html = ""
    if status == STATUS_QUEUED:
        arrows_html = (
            "<div class='arrow-row'>"
            + render_link_button("⬆️", {"action": "up", "id": row_id})
            + render_link_button("⬇️", {"action": "down", "id": row_id})
            + "</div>"
        )

    top_html = f"""
    <div class="{content_class}">
        <div class="queue-top">
            <div class="queue-left">
                <div class="queue-code">{html_lib.escape(code_display)}</div>
            </div>

            <div class="queue-right">
                <div class="queue-meta">
                    <b>Status:</b> {status_display}<br>
                    <b>Toilet:</b> {html_lib.escape(toilet_label)}<br>
                    <b>Assigned:</b> {html_lib.escape(assigned_at)}<br>
                    {returned_html}
                </div>
                {arrows_html}
            </div>
        </div>
    </div>
    """

    st.markdown(top_html, unsafe_allow_html=True)

    if status == STATUS_QUEUED:
        assign_html = (
            "<div class='assign-title'>Assign Toilet</div>"
            "<div class='assign-row'>"
            + render_link_button("🚹 Male", {"action": "assign", "id": row_id, "toilet": "Male"})
            + render_link_button("🚺 Female", {"action": "assign", "id": row_id, "toilet": "Female"})
            + render_link_button("♿ Handicap", {"action": "assign", "id": row_id, "toilet": "Handicap"})
            + "</div>"
        )

        st.markdown(assign_html, unsafe_allow_html=True)

    elif status == STATUS_IN_PROGRESS:
        action_html = (
            "<div class='action-row'>"
            + render_link_button("📣 Nudge", {"action": "nudge", "id": row_id})
            + render_link_button("✅ Return", {"action": "return", "id": row_id}, primary=True)
            + "</div>"
        )

        st.markdown(action_html, unsafe_allow_html=True)

    elif status == STATUS_RETURNED:
        st.caption("Returned — will hide after 10 seconds.")


# Handle URL actions after helper functions are ready
handle_query_actions()


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
st.markdown(
    "<div class='app-title'>🚻 Toilet Queue</div>",
    unsafe_allow_html=True,
)

st.markdown("<div class='section-title'>Gender</div>", unsafe_allow_html=True)
render_gender_selector()

st.markdown("<div class='small-title'>➕ Add Student</div>", unsafe_allow_html=True)

seat_display = st.session_state.seat_no_text or "—"

st.markdown(
    f"<div class='seat-display'>{html_lib.escape(seat_display)}</div>",
    unsafe_allow_html=True,
)

render_html_numpad()

preview_code = (
    get_queue_code(st.session_state.seat_no_text, st.session_state.selected_gender)
    if st.session_state.seat_no_text
    else "-"
)

st.markdown(
    f"<div class='preview-box'>Queue Code: {html_lib.escape(preview_code)}</div>",
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
        f"<div class='{note_class}'>{html_lib.escape(st.session_state.last_action_message)}</div>",
        unsafe_allow_html=True,
    )


# =========================================================
# ACTIVE QUEUE SECTION
# =========================================================
st.markdown("<div class='section-title'>📋 Active Queue</div>", unsafe_allow_html=True)

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
        with st.container(border=True):
            render_queue_card(index, row)


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

        st.dataframe(df_display, use_container_width=True, hide_index=True)

        csv = df.to_csv(index=False).encode("utf-8-sig")

        st.download_button(
            label="Download CSV",
            data=csv,
            file_name="toilet_queue_log.csv",
            mime="text/csv",
            use_container_width=True,
        )