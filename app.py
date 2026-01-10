import streamlit as st
import json
import os
import hashlib
import re
from datetime import datetime, date

USERS_FILE = "users.json"
CAPSULES_FILE = "capsules.json"
UPLOAD_DIR = "uploads"

os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------------- HELPERS ----------------

def hash_text(text):
    return hashlib.sha256(text.encode()).hexdigest()

def valid_password(pw):
    return bool(re.fullmatch(r"[A-Za-z0-9]+", pw))

def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

def today():
    return date.today()

# ---------------- SESSION ----------------

if "user" not in st.session_state:
    st.session_state.user = None

# ---------------- LOGIN / SIGNUP ----------------

st.title("⏳ Time Capsule")

users = load_json(USERS_FILE, {})

if st.session_state.user is None:
    st.subheader("Login / Create Account")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    st.caption("Password must contain only letters and numbers")

    if st.button("Continue"):
        if not username or not password:
            st.error("All fields required")
            st.stop()

        if not valid_password(password):
            st.error("Password must contain only letters and numbers")
            st.stop()

        hashed = hash_text(password)

        # LOGIN
        if username in users:
            if users[username] == hashed:
                st.session_state.user = username
                st.success("Login successful")
                st.rerun()
            else:
                st.error("Incorrect password")
        # SIGNUP
        else:
            users[username] = hashed
            save_json(USERS_FILE, users)
            st.session_state.user = username
            st.success("Account created")
            st.rerun()

    st.stop()

# ---------------- DASHBOARD ----------------

user = st.session_state.user
st.success(f"Welcome, {user}")

capsules = load_json(CAPSULES_FILE, [])

choice = st.radio(
    "Choose an option",
    ["Create Capsule", "View Capsules Received", "View Capsules You Created"]
)

# ---------------- CREATE CAPSULE ----------------

if choice == "Create Capsule":
    st.header("📦 Create Capsule")

    receiver = st.text_input("Receiver username")
    unlock_date = st.date_input("Unlock date", min_value=today())
    cap_pw = st.text_input("Capsule password", type="password")
    message = st.text_area("Message")
    image = st.file_uploader("Optional image", ["jpg", "png", "jpeg"])

    if st.button("Create Capsule"):
        if not receiver or not cap_pw or not message:
            st.error("All fields except image are required")
            st.stop()

        if not valid_password(cap_pw):
            st.error("Capsule password must be letters and numbers only")
            st.stop()

        img_path = ""
        if image:
            img_path = f"{UPLOAD_DIR}/{datetime.now().timestamp()}_{image.name}"
            with open(img_path, "wb") as f:
                f.write(image.read())

        capsules.append({
            "sender": user,
            "receiver": receiver,
            "unlock_date": unlock_date.isoformat(),
            "capsule_pw_hash": hash_text(cap_pw),
            "message": message,
            "image_path": img_path
        })

        save_json(CAPSULES_FILE, capsules)
        st.success("Capsule created successfully")

# ---------------- VIEW RECEIVED ----------------

elif choice == "View Capsules Received":
    st.header("📬 Capsules Sent To You")

    found = False

    for idx, cap in enumerate(capsules):
        if cap.get("receiver") != user:
            continue

        found = True
        st.subheader(f"Capsule from {cap.get('sender')}")

        unlock = datetime.fromisoformat(cap["unlock_date"]).date()
        if today() < unlock:
            st.info(f"🔒 Unlocks on {unlock}")
            continue

        pw = st.text_input(
            "Capsule password",
            type="password",
            key=f"recv_{idx}"
        )

        if pw and hash_text(pw) == cap.get("capsule_pw_hash"):
            st.success("Unlocked")
            st.write(cap.get("message"))

            img = cap.get("image_path")
            if img and os.path.exists(img):
                st.image(img)
        elif pw:
            st.error("Incorrect capsule password")

    if not found:
        st.info("No capsules received")

# ---------------- VIEW CREATED ----------------

elif choice == "View Capsules You Created":
    st.header("📝 Capsules You Created")

    found = False

    for cap in capsules:
        if cap.get("sender") != user:
            continue

        found = True
        st.subheader(f"To {cap.get('receiver')}")
        st.write(f"Unlock date: {cap.get('unlock_date')}")
        st.write(cap.get("message"))

        img = cap.get("image_path")
        if img and os.path.exists(img):
            st.image(img)

    if not found:
        st.info("No capsules created")

# ---------------- LOGOUT ----------------

st.divider()
if st.button("Logout"):
    st.session_state.user = None
    st.rerun()
