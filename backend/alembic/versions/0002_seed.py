"""seed: 6 users + 8 cases + 12 documents + activity + notifications

Revision ID: 0002_seed
Revises: 0001_initial
Create Date: 2026-06-04 23:55:00.000000
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from passlib.context import CryptContext


# revision identifiers, used by Alembic.
revision: str = "0002_seed"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# Seed data — ported verbatim from frontend/src/lib/case-mock-data.ts
# (the original frontend mock, kept in lockstep so the demo experience
# after Phase A matches the pre-MySQL CP1 demo).
# ---------------------------------------------------------------------------

PWD = CryptContext(schemes=["bcrypt"], deprecated="auto").hash("password123")

USERS = [
    # (id, email, full_name, role, court)
    ("judge-karimov",   "karimov@sud.uz",   "Hon. Rustam Karimov",     "judge",     "Tashkent City Court"),
    ("judge-yusupov",   "yusupov@sud.uz",   "Hon. Dilshod Yusupov",    "judge",     "Yunusabad District Court"),
    ("judge-rakhimova", "rakhimova@sud.uz", "Hon. Malika Rakhimova",   "judge",     "Mirzo-Ulugʻbek District Court"),
    ("asst-tursunov",   "tursunov@sud.uz",  "L. Tursunov",             "assistant", None),
    ("asst-saidova",    "saidova@sud.uz",   "N. Saidova",              "assistant", None),
    ("asst-mirzaev",    "mirzaev@sud.uz",   "B. Mirzaev",              "assistant", None),
]

CASES = [
    # (id, case_number, citizen_name, description, status, judge, assistant, return_reason)
    ("case-0241", "CASE-2026-0241", "A. Abdullayev",
     "Plaintiff seeks judicial review of the Tashkent City Administration decision denying a construction permit.",
     "under_review", "judge-karimov", "asst-tursunov", None),
    ("case-0239", "CASE-2026-0239", "M. Nazarova",
     "Inheritance dispute between two heirs; includes one appeal of the district court ruling.",
     "returned", "judge-yusupov", "asst-saidova",
     "The appeal filing is missing page 4 of the original statement. Please re-upload the full document and add a brief explanation memo."),
    ("case-0235", "CASE-2026-0235", "LLC \"Tashkent Stroy\"",
     "Procurement complaint — bidder challenges the Ministry of Finance evaluation results.",
     "approved", "judge-rakhimova", "asst-tursunov", None),
    ("case-0231", "CASE-2026-0231", "S. Mirzaev",
     "Labour dispute against JSC \"Uzbekneftegaz\" — wrongful termination claim.",
     "approved", "judge-karimov", "asst-mirzaev", None),
    ("case-0228", "CASE-2026-0228", "LLC \"Bunyodkor\"",
     "Contractual dispute — incomplete delivery of construction materials by LLC \"Kapremstroy\".",
     "approved", "judge-yusupov", "asst-mirzaev", None),
    ("case-0224", "CASE-2026-0224", "R. Aliyev",
     "Administrative violation — appeal of a fine issued by the MVD inspectorate.",
     "returned", "judge-rakhimova", "asst-saidova",
     "The counterclaim references events outside the statute of limitations. Add a written explanation of why the claim is still admissible."),
    ("case-0219", "CASE-2026-0219", "B. Salimov",
     "Property rights — disputed ownership of a residential plot in Yunusabad district.",
     "uploaded", "judge-yusupov", "asst-saidova", None),
    ("case-0214", "CASE-2026-0214", "N. Yusupova",
     "Family matter — division of jointly-held property following dissolution of marriage.",
     "draft", "judge-karimov", "asst-tursunov", None),
]

# (id, file_name, file_type, size_bytes, category, detected_type, label, confidence, uploader, iso_ts, case_id)
DOCUMENTS = [
    ("doc-001", "Claim_Abdullayev_v_City.pdf",       "pdf",  1_842_000, "procedural",  "claim",                "Claim",                96, "asst-tursunov", "2026-06-02T10:30:00", "case-0241"),
    ("doc-002", "Evidence_Contract_2024.pdf",        "pdf",  2_104_500, "evidence",    "contract",             "Contract",             91, "asst-tursunov", "2026-06-02T10:32:00", "case-0241"),
    ("doc-003", "ID_Abdullayev.jpg",                 "jpg",    845_000, "evidence",    "personal_document",    "Personal Document",    88, "asst-tursunov", "2026-06-02T10:33:00", "case-0241"),
    ("doc-004", "Appeal_Nazarova.docx",              "docx",   412_000, "procedural",  "appeal",               "Appeal",               93, "asst-saidova",  "2026-06-01T14:10:00", "case-0239"),
    ("doc-005", "Explanation_Mirzaev.pdf",           "pdf",  1_220_000, "participant", "explanation",          "Explanation",          84, "asst-mirzaev",  "2026-05-30T09:00:00", "case-0231"),
    ("doc-006", "Financial_Report_2025.pdf",         "pdf",  3_540_000, "evidence",    "financial_document",   "Financial Document",   89, "asst-tursunov", "2026-06-02T10:34:00", "case-0241"),
    ("doc-007", "Statement_Aliyev.pdf",              "pdf",    612_000, "procedural",  "statement",            "Statement",            90, "asst-saidova",  "2026-05-28T11:45:00", "case-0224"),
    ("doc-008", "Court_Resolution_0228.pdf",         "pdf",    980_000, "court",       "court_resolution",     "Court Resolution",     95, "asst-mirzaev",  "2026-05-25T16:20:00", "case-0231"),
    ("doc-009", "Objection_Plaintiff.pdf",           "pdf",    740_000, "participant", "objection",            "Objection",            87, "asst-tursunov", "2026-06-02T10:36:00", "case-0241"),
    ("doc-010", "Hearing_Transcript_0219.pdf",       "pdf",  2_010_000, "court",       "hearing_transcript",   "Hearing Transcript",   92, "asst-saidova",  "2026-05-29T13:00:00", "case-0219"),
    ("doc-011", "Counterclaim_0224.pdf",             "pdf",    880_000, "procedural",  "counterclaim",         "Counterclaim",         86, "asst-mirzaev",  "2026-05-30T09:05:00", "case-0224"),
    ("doc-012", "Additional_Statement_Yusupova.docx","docx",   220_000, "participant", "additional_statement", "Additional Statement", 81, "asst-tursunov", "2026-06-02T10:38:00", None),  # orphan
]

# (id, case_id, type, actor_id, actor_name, actor_role, message_key, iso_ts, meta_json_or_none)
ACTIVITY = [
    # case-0241 (under_review)
    ("act-0241-1", "case-0241", "case_created",         "asst-tursunov", "L. Tursunov",        "assistant", "activity.case_created",          "2026-06-02T10:25:00", None),
    ("act-0241-2", "case-0241", "documents_uploaded",   "asst-tursunov", "L. Tursunov",        "assistant", "activity.documents_uploaded",    "2026-06-02T10:35:00", '{"count": 5}'),
    ("act-0241-3", "case-0241", "documents_classified", "asst-tursunov", "AI Engine",          "assistant", "activity.documents_classified",  "2026-06-02T10:36:00", '{"count": 5}'),
    ("act-0241-4", "case-0241", "case_submitted",       "asst-tursunov", "L. Tursunov",        "assistant", "activity.case_submitted",        "2026-06-02T10:45:00", None),
    # case-0239 (returned)
    ("act-0239-1", "case-0239", "case_created",         "asst-saidova",  "N. Saidova",         "assistant", "activity.case_created",          "2026-05-28T09:00:00", None),
    ("act-0239-2", "case-0239", "documents_uploaded",   "asst-saidova",  "N. Saidova",         "assistant", "activity.documents_uploaded",    "2026-05-28T09:15:00", '{"count": 1}'),
    ("act-0239-3", "case-0239", "case_submitted",       "asst-saidova",  "N. Saidova",         "assistant", "activity.case_submitted",        "2026-05-28T09:20:00", None),
    ("act-0239-4", "case-0239", "case_returned",        "judge-yusupov", "Hon. Dilshod Yusupov","judge",    "activity.case_returned",         "2026-06-01T15:30:00", None),
    # case-0235 (approved)
    ("act-0235-1", "case-0235", "case_created",         "asst-tursunov", "L. Tursunov",        "assistant", "activity.case_created",          "2026-05-20T11:00:00", None),
    ("act-0235-2", "case-0235", "documents_uploaded",   "asst-tursunov", "L. Tursunov",        "assistant", "activity.documents_uploaded",    "2026-05-20T11:30:00", '{"count": 1}'),
    ("act-0235-3", "case-0235", "case_submitted",       "asst-tursunov", "L. Tursunov",        "assistant", "activity.case_submitted",        "2026-05-22T09:00:00", None),
    ("act-0235-4", "case-0235", "case_approved",        "judge-rakhimova","Hon. Malika Rakhimova","judge",  "activity.case_approved",         "2026-05-26T10:00:00", None),
    # case-0214 (draft, empty)
    ("act-0214-1", "case-0214", "case_created",         "asst-tursunov", "L. Tursunov",        "assistant", "activity.case_created",          "2026-06-04T08:00:00", None),
    # case-0219 (uploaded)
    ("act-0219-1", "case-0219", "case_created",         "asst-saidova",  "N. Saidova",         "assistant", "activity.case_created",          "2026-06-03T11:00:00", None),
    ("act-0219-2", "case-0219", "documents_uploaded",   "asst-saidova",  "N. Saidova",         "assistant", "activity.documents_uploaded",    "2026-06-03T11:30:00", '{"count": 1}'),
    # Bonus: doc upload events for case-0231, case-0224, case-0228 (covered by 0235/0239 above in the original mock, but adding completeness)
    ("act-0231-1", "case-0231", "case_created",         "asst-mirzaev",  "B. Mirzaev",         "assistant", "activity.case_created",          "2026-05-15T08:30:00", None),
    ("act-0224-1", "case-0224", "case_created",         "asst-saidova",  "N. Saidova",         "assistant", "activity.case_created",          "2026-05-25T10:00:00", None),
]


def _row_exists(bind, table: str, col: str, value: str) -> bool:
    """Return True if a row exists with the given column value. Used to make
    the seed migration idempotent — re-running ``alembic upgrade head`` will
    not duplicate rows.
    """
    res = bind.execute(
        sa.text(f"SELECT 1 FROM {table} WHERE {col} = :v LIMIT 1"),
        {"v": value},
    ).first()
    return res is not None


def upgrade() -> None:
    bind = op.get_bind()

    # ------------------------------------------------------------------
    # users
    # ------------------------------------------------------------------
    for uid, email, full_name, role, court in USERS:
        if _row_exists(bind, "users", "email", email):
            continue
        bind.execute(
            sa.text(
                "INSERT INTO users (id, email, full_name, hashed_password, role, court) "
                "VALUES (:id, :email, :full_name, :hashed_password, :role, :court)"
            ),
            {
                "id": uid,
                "email": email,
                "full_name": full_name,
                "hashed_password": PWD,
                "role": role,
                "court": court,
            },
        )

    # ------------------------------------------------------------------
    # cases
    # ------------------------------------------------------------------
    case_created_at = {
        "case-0241": "2026-06-02T10:25:00",
        "case-0239": "2026-05-28T09:00:00",
        "case-0235": "2026-05-20T11:00:00",
        "case-0231": "2026-05-15T08:30:00",
        "case-0228": "2026-05-10T13:00:00",
        "case-0224": "2026-05-25T10:00:00",
        "case-0219": "2026-06-03T11:00:00",
        "case-0214": "2026-06-04T08:00:00",
    }
    for cid, num, name, desc, status, judge, assistant, reason in CASES:
        if _row_exists(bind, "cases", "case_number", num):
            continue
        bind.execute(
            sa.text(
                "INSERT INTO cases (id, case_number, citizen_name, description, status, "
                "assigned_judge_id, assistant_id, return_reason, created_at, updated_at) "
                "VALUES (:id, :num, :name, :desc, :status, :judge, :assistant, :reason, :ts, :ts)"
            ),
            {
                "id": cid, "num": num, "name": name, "desc": desc, "status": status,
                "judge": judge, "assistant": assistant, "reason": reason,
                "ts": case_created_at[cid],
            },
        )

    # ------------------------------------------------------------------
    # documents (Phase B endpoints, table seeded now for the demo)
    # ------------------------------------------------------------------
    for d in DOCUMENTS:
        (did, fname, ftype, size, cat, dtype, label, conf, uploader, ts, cid) = d
        if _row_exists(bind, "documents", "id", did):
            continue
        bind.execute(
            sa.text(
                "INSERT INTO documents (id, case_id, uploader_id, file_name, file_type, size_bytes, "
                "storage_path, category, detected_type, detected_type_label, ai_confidence, uploaded_at) "
                "VALUES (:id, :cid, :uploader, :fname, :ftype, :size, :path, :cat, :dtype, :label, :conf, :ts)"
            ),
            {
                "id": did,
                "cid": cid,
                "uploader": uploader,
                "fname": fname,
                "ftype": ftype,
                "size": size,
                # Real files are not on disk yet (Phase B). The path is a
                # sentinel so any future download endpoint can return 404
                # cleanly instead of crashing on a missing file.
                "path": f"seed/{did}.{ftype}",
                "cat": cat,
                "dtype": dtype,
                "label": label,
                "conf": conf,
                "ts": ts,
            },
        )

    # ------------------------------------------------------------------
    # activity_events
    # ------------------------------------------------------------------
    for a in ACTIVITY:
        (aid, cid, atype, actor_id, actor_name, actor_role, msg_key, ts, meta) = a
        if _row_exists(bind, "activity_events", "id", aid):
            continue
        bind.execute(
            sa.text(
                "INSERT INTO activity_events (id, case_id, type, actor_id, message_key, meta, at) "
                "VALUES (:id, :cid, :type, :actor, :msg, :meta, :ts)"
            ),
            {
                "id": aid, "cid": cid, "type": atype, "actor": actor_id,
                "msg": msg_key, "meta": meta, "ts": ts,
            },
        )

    # ------------------------------------------------------------------
    # notifications — three unread notifications for the demo.
    # Timestamps anchored to "now" so the bell badge shows fresh items.
    # ------------------------------------------------------------------
    now = datetime.utcnow()
    n_recent = (now - timedelta(hours=2)).replace(microsecond=0)
    n_pending = (now - timedelta(hours=6)).replace(microsecond=0)
    n_older = (now - timedelta(hours=20)).replace(microsecond=0)

    notif_seed = [
        ("notif-1", "judge-karimov",   "case-0241", "case_submitted_to_judge",     "notification.case_submitted_to_judge",     n_recent),
        ("notif-2", "asst-tursunov",   "case-0239", "case_returned_to_assistant",  "notification.case_returned_to_assistant",  n_pending),
        ("notif-3", "asst-tursunov",   "case-0235", "case_approved",               "notification.case_approved",               n_older),
    ]
    for nid, recipient, cid, kind, msg_key, ts in notif_seed:
        if _row_exists(bind, "notifications", "id", nid):
            continue
        bind.execute(
            sa.text(
                "INSERT INTO notifications (id, recipient_id, case_id, kind, message_key, `read`, at) "
                "VALUES (:id, :recipient, :cid, :kind, :msg, 0, :ts)"
            ),
            {
                "id": nid, "recipient": recipient, "cid": cid,
                "kind": kind, "msg": msg_key, "ts": ts,
            },
        )


def downgrade() -> None:
    # We only delete the seeded notifications (they were just created in this
    # migration). Cases / docs / activity carry IDs that match the demo
    # expectation; a downgrade that removes them would leave the DB in a
    # state that surprises the next "alembic upgrade head". So the downgrade
    # is intentionally narrow.
    op.execute("DELETE FROM notifications WHERE id IN ('notif-1', 'notif-2', 'notif-3')")
