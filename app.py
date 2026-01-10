import streamlit as st
import sqlite3
import hashlib
import os
from datetime import datetime, date

# ---------------- CONFIG ----------------
DB_FILE = "time_capsule.db"
IMAGE_DIR = "uploads"
os.makedirs(IMAGE_DIR, exist_ok=True)

# ---------------- DB ----------------
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password_hash TEXT,
    is_admin INTEGER DEFAULT 0
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS capsules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender TEXT,
    receiver TEXT,
    unlock_date TEXT,
    capsule_pw_hash TEXT,
    message TEXT,
    image_path TEXT,
    edit_count INTEGER DEFAULT 0,
    admin_override INTEGER DEFAULT 0,
    edit_request INTEGER DEFAULT 0
)
""")
conn.commit()

# ---------------- HELPERS ----------------
def hash_text(t):
    return hashlib.sha256(t.encode()).hexdigest()

def today():
    return date.today()

# ---------------- SESSION ----------------
if "user" not in st.session_state:
    st.session_state.user = None
    st.session_state.is_admin = False

# ---------------- LOGIN ----------------
st.title("⏳ Time Capsule")

if st.session_state.user is None:
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Continue"):
        c.execute("SELECT password_hash, is_admin FROM users WHERE username=?", (u,))
        row = c.fetchone()

        if row:
            if hash_text(p) == row[0]:
                st.session_state.user = u
                st.session_state.is_admin = bool(row[1])
                st.rerun()
            else:
                st.error("Wrong password")
        else:
            c.execute("SELECT COUNT(*) FROM users")
            is_admin = 1 if c.fetchone()[0] == 0 else 0

            c.execute(
                "INSERT INTO users VALUES (?,?,?)",
                (u, hash_text(p), is_admin)
            )
            conn.commit()

            st.session_state.user = u
            st.session_state.is_admin = bool(is_admin)
            st.success("Account created")
            st.rerun()

    st.stop()

user = st.session_state.user
is_admin = st.session_state.is_admin
st.success(f"Logged in as {user}" + (" (Admin)" if is_admin else ""))

menu = st.radio(
    "Menu",
    ["Create Capsule", "View Capsules Received", "View Capsules You Created"] +
    (["Admin Panel"] if is_admin else [])
)

# ---------------- CREATE CAPSULE ----------------
if menu == "Create Capsule":
    receiver = st.text_input("Receiver username")
    unlock = st.date_input("Unlock date", min_value=today())
    cap_pw = st.text_input("Capsule password", type="password")
    msg = st.text_area("Message")
    img = st.file_uploader("Optional image", ["png", "jpg", "jpeg"])

    if st.button("Create Capsule"):
        img_path = ""
        if img:
            img_path = f"{IMAGE_DIR}/{datetime.now().timestamp()}_{img.name}"
            with open(img_path, "wb") as f:
                f.write(img.read())

        c.execute("""
        INSERT INTO capsules
        (sender, receiver, unlock_date, capsule_pw_hash, message, image_path)
        VALUES (?,?,?,?,?,?)
        """, (user, receiver, unlock.isoformat(), hash_text(cap_pw), msg, img_path))
        conn.commit()
        st.success("Capsule created")

# ---------------- VIEW RECEIVED ----------------
elif menu == "View Capsules Received":
    c.execute("SELECT * FROM capsules WHERE receiver=?", (user,))
    rows = c.fetchall()

    if not rows:
        st.info("No capsules received")
    else:
        for r in rows:
            cid, sender, _, unlock, pw_hash, msg, img, *_ = r
            unlock_d = datetime.fromisoformat(unlock).date()

            st.subheader(f"From {sender} (#{cid})")

            if today() < unlock_d:
                st.warning(f"Locked until {unlock_d}")
                continue

            pw = st.text_input("Capsule password", type="password", key=f"open{cid}")
            if pw and hash_text(pw) == pw_hash:
                st.success("Unlocked")
                st.write(msg)
                if img and os.path.exists(img):
                    st.image(img)

# ---------------- VIEW CREATED ----------------
elif menu == "View Capsules You Created":
    c.execute("SELECT * FROM capsules WHERE sender=?", (user,))
    rows = c.fetchall()

    if not rows:
        st.info("You haven't created any capsules")
    else:
        for r in rows:
            cid, _, recv, unlock, _, msg, img, edits, override, req = r
            unlock_d = datetime.fromisoformat(unlock).date()

            st.subheader(f"To {recv} (#{cid})")
            st.write(f"Edits used: {edits}/3")
            st.write(f"Unlock date: {unlock_d}")

            can_edit = today() < unlock_d and (edits < 3 or override)

            if can_edit:
                with st.expander("✏️ Edit Capsule"):
                    new_msg = st.text_area("Message", msg, key=f"edit_{cid}")

                    if st.button("Save Edit", key=f"save_{cid}"):
                        c.execute("""
                        UPDATE capsules
                        SET message=?, edit_count=edit_count+1
                        WHERE id=?
                        """, (new_msg, cid))
                        conn.commit()
                        st.success("Capsule updated")
                        st.rerun()
            else:
                st.warning("Editing locked")

                if today() < unlock_d and not req:
                    if st.button("Request admin permission", key=f"req_{cid}"):
                        c.execute(
                            "UPDATE capsules SET edit_request=1 WHERE id=?",
                            (cid,)
                        )
                        conn.commit()
                        st.success("Request sent to admin")
                        st.rerun()

                elif req:
                    st.info("Admin approval pending")

# ---------------- ADMIN PANEL ----------------
elif menu == "Admin Panel":
    st.header("🛠 Edit Permission Requests")

    c.execute("""
    SELECT id, sender, edit_count 
    FROM capsules WHERE edit_request=1
    """)
    rows = c.fetchall()

    if not rows:
        st.info("No pending requests")
    else:
        for cid, sender, edits in rows:
            st.write(f"Capsule #{cid} by {sender} (edits used: {edits})")

            if st.button(f"Approve edits for #{cid}", key=f"approve_{cid}"):
                c.execute("""
                UPDATE capsules
                SET admin_override=1, edit_request=0
                WHERE id=?
                """, (cid,))
                conn.commit()
                st.success("Edit permission granted")
                st.rerun()

# ---------------- LOGOUT ----------------
st.divider()
if st.button("Logout"):
    st.session_state.user = None
    st.session_state.is_admin = False
    st.rerun()
