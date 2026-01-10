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
    password_hash TEXT
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
    image_path TEXT
)
""")
conn.commit()

# ---------------- HELPERS ----------------
def hash_text(text):
    return hashlib.sha256(text.encode()).hexdigest()

def today():
    return date.today()

# ---------------- SESSION ----------------
if "user" not in st.session_state:
    st.session_state.user = None

# ---------------- LOGIN ----------------
st.title("⏳ Time Capsule")

if st.session_state.user is None:
    st.subheader("Login / Sign Up")

    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Continue"):
        if not u or not p:
            st.error("All fields required")
            st.stop()

        c.execute("SELECT password_hash FROM users WHERE username=?", (u,))
        row = c.fetchone()

        if row:
            if hash_text(p) == row[0]:
                st.session_state.user = u
                st.rerun()
            else:
                st.error("Wrong password")
        else:
            c.execute(
                "INSERT INTO users VALUES (?,?)",
                (u, hash_text(p))
            )
            conn.commit()
            st.session_state.user = u
            st.success("Account created")
            st.rerun()

    st.stop()

# ---------------- DASHBOARD ----------------
user = st.session_state.user
st.success(f"Logged in as {user}")

menu = st.radio(
    "Choose",
    ["Create Capsule", "View Capsules Received", "View Capsules You Created"]
)

# ---------------- CREATE ----------------
if menu == "Create Capsule":
    st.header("📦 Create Capsule")

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
        """, (
            user,
            receiver,
            unlock.isoformat(),
            hash_text(cap_pw),
            msg,
            img_path
        ))
        conn.commit()
        st.success("Capsule created")

# ---------------- VIEW RECEIVED ----------------
elif menu == "View Capsules Received":
    st.header("📬 Capsules Sent To You")

    c.execute("SELECT * FROM capsules WHERE receiver=?", (user,))
    rows = c.fetchall()

    if not rows:
        st.info("No capsules")
    else:
        for r in rows:
            cid, sender, _, unlock, pw_hash, msg, img_path = r
            unlock_date = datetime.fromisoformat(unlock).date()

            st.subheader(f"From {sender} (Capsule #{cid})")

            if today() < unlock_date:
                st.warning(f"Locked until {unlock_date}")
                continue

            pw = st.text_input(
                "Capsule password",
                type="password",
                key=f"open_{cid}"
            )

            if pw and hash_text(pw) == pw_hash:
                st.success("Unlocked")
                st.write(msg)
                if img_path and os.path.exists(img_path):
                    st.image(img_path)

# ---------------- VIEW CREATED ----------------
elif menu == "View Capsules You Created":
    st.header("📝 Capsules You Created")

    c.execute("SELECT * FROM capsules WHERE sender=?", (user,))
    rows = c.fetchall()

    if not rows:
        st.info("None created")
    else:
        for r in rows:
            cid, _, receiver, unlock, _, msg, img_path = r
            unlock_date = datetime.fromisoformat(unlock).date()

            st.subheader(f"To {receiver} (Capsule #{cid})")
            st.write(f"Unlocks on: {unlock_date}")
            st.write(msg)

            if img_path and os.path.exists(img_path):
                st.image(img_path)

            # 🔒 DELETE LOGIC
            if today() < unlock_date:
                if st.button("❌ Delete Capsule", key=f"del_{cid}"):
                    c.execute("DELETE FROM capsules WHERE id=?", (cid,))
                    conn.commit()
                    st.success("Capsule deleted")
                    st.rerun()
            else:
                st.info("🔒 Cannot delete after unlock")

# ---------------- LOGOUT ----------------
st.divider()
if st.button("Logout"):
    st.session_state.user = None
    st.rerun()
