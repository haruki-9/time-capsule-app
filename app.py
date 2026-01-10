import streamlit as st
import json
import os
from datetime import datetime

DATA_FILE = "capsules.json"

# ----------------- helpers -----------------

def load_capsules():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_capsules(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def today():
    return datetime.now().date()

# ----------------- session -----------------

if "user" not in st.session_state:
    st.session_state.user = None

# ----------------- login -----------------

st.title("⏳ Time Capsule")

if st.session_state.user is None:
    username = st.text_input("Enter your username")
    if st.button("Login") and username.strip():
        st.session_state.user = username.strip()
        st.rerun()
    st.stop()

st.success(f"Welcome, {st.session_state.user}")

capsules = load_capsules()

choice = st.radio(
    "Choose an option",
    ["Create Capsule", "View Capsules Received", "View Capsules You Created"]
)

# ----------------- create capsule -----------------

if choice == "Create Capsule":
    st.header("📦 Create Capsule")

    receiver = st.text_input("Receiver username")
    unlock_date = st.date_input("Unlock date")
    password = st.text_input("Capsule password", type="password")
    message = st.text_area("Message")

    uploaded_image = st.file_uploader("Optional image", type=["png", "jpg", "jpeg"])

    if st.button("Create Capsule"):
        image_path = ""

        if uploaded_image:
            os.makedirs("uploads", exist_ok=True)
            image_path = f"uploads/{datetime.now().timestamp()}_{uploaded_image.name}"
            with open(image_path, "wb") as f:
                f.write(uploaded_image.read())

        capsules.append({
            "sender": st.session_state.user,
            "receiver": receiver,
            "unlock_date": str(unlock_date),
            "password": password,
            "message": message,
            "image_path": image_path
        })

        save_capsules(capsules)
        st.success("Capsule created successfully!")

# ----------------- view received -----------------

elif choice == "View Capsules Received":
    st.header("📥 Capsules Sent To You")

    found = False

    for i, cap in enumerate(capsules, 1):
        if cap["receiver"] != st.session_state.user:
            continue

        found = True
        st.subheader(f"Capsule #{i} from {cap['sender']}")

        if today() < datetime.fromisoformat(cap["unlock_date"]).date():
            st.warning(f"Unlocks on {cap['unlock_date']}")
            continue

        pwd = st.text_input(
            "Capsule password",
            type="password",
            key=f"recv_{i}"
        )

        if pwd == cap["password"]:
            st.success("Unlocked")
            st.write(cap["message"])

            # ✅ SAFE IMAGE DISPLAY
            if cap.get("image_path") and os.path.exists(cap["image_path"]):
                st.image(cap["image_path"])
        else:
            st.info("Enter password to unlock")

    if not found:
        st.info("No capsules received yet")

# ----------------- view created -----------------

elif choice == "View Capsules You Created":
    st.header("📤 Capsules You Created")

    found = False

    for i, cap in enumerate(capsules, 1):
        if cap["sender"] != st.session_state.user:
            continue

        found = True
        st.subheader(f"Capsule #{i} → {cap['receiver']}")
        st.write(f"Unlock date: {cap['unlock_date']}")
        st.write(cap["message"])

        # ✅ SAFE IMAGE DISPLAY
        if cap.get("image_path") and os.path.exists(cap["image_path"]):
            st.image(cap["image_path"])

    if not found:
        st.info("You haven't created any capsules yet")
