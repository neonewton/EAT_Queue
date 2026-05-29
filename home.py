import streamlit as st
from datetime import datetime, timezone
from supabase import create_client

password = st.text_input("Enter event password", type="LKCexam")

if password != st.secrets["APP_PASSWORD"]:
    st.stop()

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def load_queue(location):
    return (
        supabase.table("toilet_queue")
        .select("*")
        .eq("location", location)
        .in_("status", ["Queued", "Returned"])
        .order("queue_order")
        .execute()
        .data
    )


def mark_returned(row_id):
    supabase.table("toilet_queue").update({
        "status": "Returned",
        "returned_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", row_id).execute()


def move_up(row):
    new_order = max(1, row["queue_order"] - 1)
    supabase.table("toilet_queue").update({
        "queue_order": new_order
    }).eq("id", row["id"]).execute()

from datetime import datetime, timezone, timedelta

def archive_old_returned():
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=10)

    returned_rows = (
        supabase.table("toilet_queue")
        .select("*")
        .eq("status", "Returned")
        .execute()
        .data
    )

    for row in returned_rows:
        if row.get("returned_at"):
            returned_at = datetime.fromisoformat(row["returned_at"].replace("Z", "+00:00"))

            if returned_at < cutoff:
                supabase.table("toilet_queue").update({
                    "status": "Archived"
                }).eq("id", row["id"]).execute()

def move_down(row):
    new_order = row["queue_order"] + 1
    supabase.table("toilet_queue").update({
        "queue_order": new_order
    }).eq("id", row["id"]).execute()

st.set_page_config(
    page_title="Toilet Queue",
    layout="wide"
)

st.title("Toilet Queue System")

with st.form("add_student"):
    seat_no = st.number_input("Seat Number", min_value=1, step=1)
    gender = st.selectbox("Gender", ["Male", "Female"])
    location = st.selectbox("Assign to", ["Male", "Female", "Handicap"])
    submitted = st.form_submit_button("Add to Queue")

    if submitted:
        prefix = "M" if gender == "Male" else "F"
        queue_code = f"{prefix}{seat_no}"

        existing = (
            supabase.table("toilet_queue")
            .select("*")
            .eq("status", "Queued")
            .execute()
            .data
        )

        next_order = len(existing) + 1

        supabase.table("toilet_queue").insert({
            "queue_code": queue_code,
            "seat_no": seat_no,
            "gender": gender,
            "location": location,
            "status": "Queued",
            "queue_order": next_order,
            "assigned_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        st.success(f"Added {queue_code} to {location} queue")
        st.rerun()