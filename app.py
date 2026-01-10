import streamlit as st
import pandas as pd
import os
import hashlib
from datetime import date

# ---------------- CONFIG ----------------
DATA_FILE = "capsules.csv"
IMAGE_DIR = "images"

USERS = {
    "Bhanu": "bhanu123",
    "Friend": "friend123"
}

# ---------------- HELPERS ----------------
def hash_text(text):
    return hashlib.sha256(text.encode()).hexdigest()

def load_data():
    if not os.path.exists(DATA_FILE):
        return pd.DataFrame(columns=[
            "id", "creator", "recipient",
            "message", "image", "unlock_date",
            "password_hash"
        ])
    return pd.read_csv(DATA_FILE)

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

os.makedirs(IMAGE_DIR, exist_ok=True)

# ---------------- SESSION ----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# ---------------- LOGIN SCREEN ----------------
st.title("⏳ Time Capsule")

if not st.session_state.logged_in:
    user = st.selectbox("Login as", USERS.keys())
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if password == USERS[user]:
            st.session_state.logged_in = True
            st.session_state.user = user
            st.success("Login successful")
            st.experimental_rerun()
        else:
            st.error("Incorrect password")

    st.stop()

# ---------------- DASHBOARD ----------------
user = st.session_state.user
df = load_data()
today = date.today()

st.success(f"Welcome, {user}")

menu = st.radio(
    "Choose an option",
    ["Create Capsule", "View Capsules Received", "View Capsules You Created"]
)

# ---------------- CREATE CAPSULE ----------------
if menu == "Create Capsule":
    st.header("📦 Create a Time Capsule")

    with st.form("create_capsule"):
        recipient = st.selectbox("Send to", USERS.keys())
        unlock_date = st.date_input("Unlock date", min_value=today)
        capsule_pw = st.text_input("Capsule password", type="password")
        message = st.text_area("Write your message")
        image = st.file_uploader("Upload image (optional)", type=["jpg", "png", "jpeg"])
        submit = st.form_submit_button("Create Capsule")

        if submit:
            if not capsule_pw or not message:
                st.error("Message and capsule password are required")
            else:
                cid = len(df) + 1
                image_path = ""

                if image:
                    image_path = f"{IMAGE_DIR}/{cid}_{image.name}"
                    with open(image_path, "wb") as f:
                        f.write(image.read())

                new_row = {
                    "id": cid,
                    "creator": user,
                    "recipient": recipient,
                    "message": message,
                    "image": image_path,
                    "unlock_date": unlock_date,
                    "password_hash": hash_text(capsule_pw)
                }

                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                save_data(df)
                st.success("Time capsule created successfully")

# ---------------- VIEW RECEIVED CAPSULES ----------------
elif menu == "View Capsules Received":
    st.header("📬 Capsules Sent To You")

    found = False
    for _, row in df.iterrows():
        if row["recipient"] != user:
            continue

        found = True
        st.subheader(f"Capsule #{row['id']} (from {row['creator']})")

        unlock = pd.to_datetime(row["unlock_date"]).date()
        if today < unlock:
            st.info(f"🔒 Locked until {unlock}")
            continue

        pw = st.text_input(
            f"Enter password for Capsule #{row['id']}",
            type="password",
            key=f"view_{row['id']}"
        )

        if pw and hash_text(pw) == row["password_hash"]:
            st.success("Unlocked")
            st.write(row["message"])
            if row["image"]:
                st.image(row["image"])

    if not found:
        st.info("No capsules received yet")

# ---------------- VIEW CREATED CAPSULES ----------------
elif menu == "View Capsules You Created":
    st.header("📝 Capsules You Created")

    found = False
    for _, row in df.iterrows():
        if row["creator"] != user:
            continue

        found = True
        st.subheader(f"Capsule #{row['id']} → {row['recipient']}")
        st.write(f"Unlock date: {row['unlock_date']}")
        st.write(row["message"])
        if row["image"]:
            st.image(row["image"])

    if not found:
        st.info("You haven't created any capsules yet")

# ---------------- LOGOUT ----------------
st.divider()
if st.button("Logout"):
    st.session_state.logged_in = False
    st.experimental_rerun()
