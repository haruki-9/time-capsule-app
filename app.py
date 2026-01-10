import streamlit as st
import sqlite3
import hashlib
import os
from datetime import datetime, date

# ----------------- CONFIG -----------------
DB_FILE = "capsules.db"
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ----------------- DB SETUP -----------------
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

# ----------------- HELPERS -----------------
def hash_text(text):
    return hashlib.sha256(text.encode()).hexdigest()

def today():
    return date.today()

# ----------------- SESSION -----------------
if "user" not in st.session_state:
    st.session_state.user = None

st.title("⏳ Time Capsule")

# ----------------- AUTH -----------------
if st.session_state.user is None:
    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        u = st.text_input("Username", key="login_u")
        p = st.text_input("Password", type="password", key="login_p")

        if st.button("Login"):
            c.execute("SELECT password_hash FROM users WHERE username=?", (u,))
            row = c.fetchone()
            if row and hash_text(p) == row[0]:
                st.session_state.user = u
                st.rerun()
            else:
                st.error("Invalid username or password")

    with tab2:
        u = st.text_input("New username", key="reg_u")
        p = st.text_input("New password", type="password", key="reg_p")

        if st.button("Register"):
            try:
                c.execute(
                    "INSERT INTO users VALUES (?,?)",
                    (u, hash_text(p))
                )
                conn.commit()
                st.success("Account created. Login now.")
            except:
                st.error("Username already exists")

    st.stop()

# ----------------- MAIN -----------------
st.success(f"Welcome, {st.session_state.user}")

choice = st.radio(
    "Choose an option",
    ["Create Capsule", "View Capsules Received", "View Capsules You Created"]
)

# ----------------- CREATE CAPSULE -----------------
if choice == "Create Capsule":
    st.header("📦 Create Capsule")

    receiver = st.text_input("Receiver username")
    unlock_date = st.date_input("Unlock date")
    capsule_pw = st.text_input("Capsule password", type="password")
    message = st.text_area("Message")
    image = st.file_uploader("Optional image", ["png", "jpg", "jpeg"])

    if st.button("Create Capsule"):
        img_path = ""

        if image:
            img_path = f"{UPLOAD_DIR}/{datetime.now().timestamp()}_{image.name}"
            with open(img_path, "wb") as f:
                f.write(image.read())

        c.execute("""
        INSERT INTO capsules
        (sender, receiver, unlock_date, capsule_pw_hash, message, image_path)
        VALUES (?,?,?,?,?,?)
        """, (
            st.session_state.user,
            receiver,
            str(unlock_date),
            hash_text(capsule_pw),
            message,
            img_path
        ))
        conn.commit()

        st.success("Capsule created successfully!")

# ----------------- VIEW RECEIVED -----------------
elif choice == "View Capsules Received":
    st.header("📥 Capsules Sent To You")

    c.execute("SELECT * FROM capsules WHERE receiver=?", (st.session_state.user,))
    rows = c.fetchall()

    if not rows:
        st.info("No capsules received yet")

    for cap in rows:
        cap_id, sender, _, unlock, pw_hash, msg, img = cap
        st.subheader(f"From {sender}")

        if today() < datetime.fromisoformat(unlock).date():
            st.warning(f"Unlocks on {unlock}")
            continue

        pw = st.text_input(
            "Capsule password",
            type="password",
            key=f"cap_{cap_id}"
        )

        if pw and hash_text(pw) == pw_hash:
            st.success("Unlocked")
            st.write(msg)

            if img and os.path.exists(img):
                st.image(img)
        else:
            st.info("Enter correct capsule password")

# ----------------- VIEW CREATED -----------------
elif choice == "View Capsules You Created":
    st.header("📤 Capsules You Created")

    c.execute("SELECT * FROM capsules WHERE sender=?", (st.session_state.user,))
    rows = c.fetchall()

    if not rows:
        st.info("You haven't created any capsules")

    for cap in rows:
        _, _, receiver, unlock, _, msg, img = cap
        st.subheader(f"To {receiver}")
        st.write(f"Unlock date: {unlock}")
        st.write(msg)

        if img and os.path.exists(img):
            st.image(img)
