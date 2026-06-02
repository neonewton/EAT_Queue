from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from supabase import create_client


# =========================================================
# CONSTANTS
# =========================================================
LOCATIONS = ["Male", "Female", "Handicap"]
GENDERS = ["Male", "Female"]

STATUS_QUEUED = "Queued"
STATUS_IN_PROGRESS = "In Progress"
STATUS_RETURNED = "Returned"
STATUS_ARCHIVED = "Archived"

ACTIVE_STATUSES = [STATUS_QUEUED, STATUS_IN_PROGRESS, STATUS_RETURNED]

SGT = ZoneInfo("Asia/Singapore")

TOILET_LABELS = {
    "Unassigned": "Not assigned",
    "Male": "🚹 Male",
    "Female": "🚺 Female",
    "Handicap": "♿ Handicap",
}


# =========================================================
# TIME HELPERS
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


# =========================================================
# VALIDATION
# =========================================================
def validate_assignment(gender, toilet):
    """
    Rules:
    - Male cannot be assigned to Female Toilet
    - Female cannot be assigned to Male Toilet
    - Both can be assigned to Handicap Toilet
    """
    if gender == "Male" and toilet == "Female":
        return False, "Male student cannot be assigned to Female Toilet."

    if gender == "Female" and toilet == "Male":
        return False, "Female student cannot be assigned to Male Toilet."

    return True, ""


# =========================================================
# BACKEND CLASS
# =========================================================
class ToiletQueueCore:
    def __init__(self, supabase_url, supabase_key):
        self.supabase = create_client(supabase_url, supabase_key)

    def _execute(self, query):
        response = query.execute()
        return response.data

    def archive_old_returned(self, seconds=10):
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=seconds)

        returned_rows = self._execute(
            self.supabase.table("toilet_queue")
            .select("*")
            .eq("status", STATUS_RETURNED)
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
                    self._execute(
                        self.supabase.table("toilet_queue")
                        .update({"status": STATUS_ARCHIVED})
                        .eq("id", row["id"])
                        .select("*")
                    )

            except Exception:
                continue

    def load_active_queue(self):
        rows = self._execute(
            self.supabase.table("toilet_queue")
            .select("*")
            .in_("status", ACTIVE_STATUSES)
            .order("queue_order")
            .order("created_at")
        )

        return rows or []

    def load_log(self):
        rows = self._execute(
            self.supabase.table("toilet_queue")
            .select("*")
            .order("created_at", desc=True)
        )

        return rows or []

    def get_next_order(self):
        rows = self._execute(
            self.supabase.table("toilet_queue")
            .select("queue_order")
            .in_("status", [STATUS_QUEUED, STATUS_IN_PROGRESS])
        )

        if not rows:
            return 1

        return max(row.get("queue_order", 0) or 0 for row in rows) + 1

    def add_student(self, seat_no, gender):
        seat_no = str(seat_no).strip()

        if not seat_no:
            return False, "Please enter a seat number."

        if not seat_no.isdigit():
            return False, "Seat number must be numeric."

        if gender not in GENDERS:
            return False, "Invalid gender selected."

        queue_code = get_queue_code(seat_no, gender)

        duplicate = self._execute(
            self.supabase.table("toilet_queue")
            .select("*")
            .eq("queue_code", queue_code)
            .in_("status", ACTIVE_STATUSES)
        )

        if duplicate:
            return False, f"{queue_code} is already active."

        next_order = self.get_next_order()

        self._execute(
            self.supabase.table("toilet_queue")
            .insert({
                "queue_code": queue_code,
                "seat_no": int(seat_no),
                "gender": gender,
                "location": "Unassigned",
                "status": STATUS_QUEUED,
                "queue_order": next_order,
                "assigned_at": None,
                "returned_at": None,
            })
        )

        return True, f"Added {queue_code} to queue."

    def assign_toilet(self, row_id, queue_code, gender, toilet):
        if toilet not in LOCATIONS:
            return False, "Invalid toilet selected."

        # Rule 1: Gender validation
        is_valid, message = validate_assignment(gender, toilet)

        if not is_valid:
            return False, message

        # Rule 2: Toilet occupancy validation
        # If the selected toilet already has someone In Progress, block assignment.
        existing_in_progress = self._execute(
            self.supabase.table("toilet_queue")
            .select("*")
            .eq("location", toilet)
            .eq("status", STATUS_IN_PROGRESS)
        )

        if existing_in_progress:
            toilet_label = TOILET_LABELS.get(toilet, toilet)
            current_user = existing_in_progress[0].get("queue_code", "another student")

            return (
                False,
                f"{toilet_label} Toilet is currently in use by {current_user}. Please wait until they return."
            )

        # Rule 3: Assign toilet and change status to In Progress
        self._execute(
            self.supabase.table("toilet_queue")
            .update({
                "location": toilet,
                "status": STATUS_IN_PROGRESS,
                "assigned_at": now_utc_iso(),
            })
            .eq("id", row_id)
            .select("*")
        )

        return True, f"{queue_code} assigned to {TOILET_LABELS[toilet]}."

    def mark_returned(self, row_id, queue_code):
        self._execute(
            self.supabase.table("toilet_queue")
            .update({
                "status": STATUS_RETURNED,
                "returned_at": now_utc_iso(),
            })
            .eq("id", row_id)
            .select("*")
        )

        return True, f"{queue_code} returned."

    def swap_queue_order(self, row_a, row_b):
        order_a = row_a["queue_order"]
        order_b = row_b["queue_order"]

        self._execute(
            self.supabase.table("toilet_queue")
            .update({"queue_order": order_b})
            .eq("id", row_a["id"])
            .select("*")
        )

        self._execute(
            self.supabase.table("toilet_queue")
            .update({"queue_order": order_a})
            .eq("id", row_b["id"])
            .select("*")
        )

    def move_up(self, row_id):
        queue = [
            row for row in self.load_active_queue()
            if row.get("status") == STATUS_QUEUED
        ]

        for index, row in enumerate(queue):
            if row["id"] == row_id and index > 0:
                self.swap_queue_order(row, queue[index - 1])
                return True, f"{row['queue_code']} moved up."

        return False, "Already at the top."

    def move_down(self, row_id):
        queue = [
            row for row in self.load_active_queue()
            if row.get("status") == STATUS_QUEUED
        ]

        for index, row in enumerate(queue):
            if row["id"] == row_id and index < len(queue) - 1:
                self.swap_queue_order(row, queue[index + 1])
                return True, f"{row['queue_code']} moved down."

        return False, "Already at the bottom."
    
    def call_student(self, row_id, queue_code):
        self._execute(
            self.supabase.table("toilet_queue")
            .update({
                "called_at": now_utc_iso(),
            })
            .eq("id", row_id)
            .select("*")
        )

        return True, f"{queue_code} called."