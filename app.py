import streamlit as st
import json
import os
import hashlib
from datetime import datetime, date

# ---------------- CONFIG ----------------
USERS_FILE = "users.json"
CAPSULES_FILE = "capsules.json"
UPLOAD_DIR = "uploads"

os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------------- HELPERS ----------------
def hash_text(text):
    return hashlib.sha256(text.encode()).hexdigest()

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

# ---------------- LOAD DATA ----------------
users = load_json(USERS_FILE, {})
capsules = load_json(CAPSULES_FILE, [])

# ---------------- TITLE ----------------
st.title("⏳ Time Capsule")

# ======================================================
# LOGIN / SIGNUP
# ======================================================
if st.session_state.user is None:
    st.subheader("Login or Create Account")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Continue"):
        if not username or not password:
            st.error("Username and password required")
            st.stop()

        pw_hash = hash_text(password)

        if username in users:
            if users[username] == pw_hash:
                st.session_state.user = username
                st.success("Login successful")
                st.rerun()
            else:
                st.error("Incorrect password")
        else:
            users[username] = pw_hash
            save_json(USERS_FILE, users)
            st.session_state.user = username
            st.success("Account created")
            st.rerun()

    st.stop()

# ======================================================
# DASHBOARD
# ======================================================
user = st.session_state.user
st.success(f"Welcome, {user}")

menu = st.radio(
    "Choose an option",
    ["Create Capsule", "View Capsules Received", "View Capsules You Created"]
)

# ======================================================
# CREATE CAPSULE
# ======================================================
if menu == "Create Capsule":
    st.header("📦 Create a Time Capsule")

    receiver = st.text_input("Send to (username)")
    unlock_date = st.date_input("Unlock date", min_value=today())
    capsule_pw = st.text_input("Capsule password", type="password")
    message = st.text_area("Message")
    image = st.file_uploader("Optional image", ["jpg", "jpeg", "png"])

    if st.button("Create Capsule"):
        if not receiver or not capsule_pw or not message:
            st.error("All fields except image are required")
            st.stop()

        image_path = ""
        if image:
            filename = f"{datetime.now().timestamp()}_{image.name}"
            image_path = os.path.join(UPLOAD_DIR, filename)
            with open(image_path, "wb") as f:
                f.write(image.read())

        capsules.append({
            "id": datetime.now().timestamp(),
            "sender": user,
            "receiver": receiver,
            "unlock_date": str(unlock_date),
            "capsule_pw_hash": hash_text(capsule_pw),
            "message": message,
            "image_path": image_path
        })

        save_json(CAPSULES_FILE, capsules)
        st.success("Capsule created successfully")

# ======================================================
# VIEW RECEIVED CAPSULES
# ======================================================
elif menu == "View Capsules Received":
    st.header("📬 Capsules Sent To You")

    found = False

    for idx, cap in enumerate(capsules):
        if cap["receiver"] != user:
            continue

        found = True
        st.subheader(f"Capsule from {cap['sender']}")

        unlock = datetime.fromisoformat(cap["unlock_date"]).date()
        if today() < unlock:
            st.info(f"🔒 Locked until {unlock}")
            continue

        pw = st.text_input(
            "Capsule password",
            type="password",
            key=f"recv_{idx}"
        )

        if pw and hash_text(pw) == cap["capsule_pw_hash"]:
            st.success("Unlocked")
            st.write(cap["message"])

            if cap["image_path"] and os.path.exists(cap["image_path"]):
                st.image(cap["image_path"])

    if not found:
        st.info("No capsules received")

# ======================================================
# VIEW / EDIT / DELETE CREATED CAPSULES
# ======================================================
elif menu == "View Capsules You Created":
    st.header("📝 Capsules You Created")

    found = False

    for idx, cap in enumerate(capsules):
        if cap["sender"] != user:
            continue

        found = True
        unlock = datetime.fromisoformat(cap["unlock_date"]).date()

        st.subheader(f"To {cap['receiver']}")
        st.write(f"Unlock date: {unlock}")

        # -------- EDIT (only before unlock) --------
        if today() < unlock:
            with st.expander("✏️ Edit Capsule"):
                new_message = st.text_area(
                    "Edit message",
                    value=cap["message"],
                    key=f"edit_{idx}"
                )

                if st.button("Save Changes", key=f"save_{idx}"):
                    cap["message"] = new_message
                    save_json(CAPSULES_FILE, capsules)
                    st.success("Capsule updated")
                    st.rerun()
        else:
            st.info("Capsule already unlocked — editing disabled")

        st.write(cap["message"])

        if cap["image_path"] and os.path.exists(cap["image_path"]):
            st.image(cap["image_path"])

        # -------- DELETE --------
        if st.button("🗑️ Delete Capsule", key=f"del_{idx}"):
            capsules.pop(idx)
            save_json(CAPSULES_FILE, capsules)
            st.success("Capsule deleted")
            st.rerun()

    if not found:
        st.info("You haven't created any capsules")

# ======================================================
# LOGOUT
# ======================================================
st.divider()
if st.button("Logout"):
    st.session_state.user = None
    st.rerun()
