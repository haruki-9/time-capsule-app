import streamlit as st
import pandas as pd
import os
import hashlib
from datetime import date

# ------------------ CONFIG ------------------
DATA_FILE = "capsules.csv"
IMAGE_DIR = "images"
MAX_EDITS = 3

USERS = {
    "Bhanu": "bhanu123",
    "Friend": "friend123"
}

ADMIN_PASSWORD = "admin123"   # later move to st.secrets

# ------------------ HELPERS ------------------
def hash_text(text):
    return hashlib.sha256(text.encode()).hexdigest()

def check_password(input_pw, stored_hash):
    return hash_text(input_pw) == stored_hash

def load_data():
    if not os.path.exists(DATA_FILE):
        return pd.DataFrame(columns=[
            "id", "creator", "recipient",
            "text", "image", "unlock_date",
            "password_hash", "edit_count"
        ])
    return pd.read_csv(DATA_FILE)

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

def ensure_dirs():
    if not os.path.exists(IMAGE_DIR):
        os.makedirs(IMAGE_DIR)

ensure_dirs()

# ------------------ LOGIN ------------------
st.title("🕰️ Time Capsule")

user = st.selectbox("Login as", list(USERS.keys()))
password = st.text_input("Password", type="password")

if password != USERS[user]:
    st.stop()

st.success(f"Logged in as {user}")

df = load_data()
today = date.today()

# ------------------ CREATE CAPSULE ------------------
st.header("Create a Time Capsule")

with st.form("create_capsule"):
    recipient = st.selectbox("Recipient", list(USERS.keys()))
    unlock_date = st.date_input("Unlock Date")
    capsule_password = st.text_input("Capsule Password", type="password")
    text = st.text_area("Message")
    image = st.file_uploader("Image (optional)", type=["png", "jpg", "jpeg"])
    submitted = st.form_submit_button("Create")

    if submitted:
        capsule_id = len(df) + 1
        image_path = ""

        if image:
            image_path = f"{IMAGE_DIR}/{capsule_id}_{image.name}"
            with open(image_path, "wb") as f:
                f.write(image.getbuffer())

        new_row = {
            "id": capsule_id,
            "creator": user,
            "recipient": recipient,
            "text": text,
            "image": image_path,
            "unlock_date": unlock_date,
            "password_hash": hash_text(capsule_password),
            "edit_count": 0
        }

        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        save_data(df)
        st.success("Capsule created!")

# ------------------ VIEW CAPSULES ------------------
st.header("Your Capsules")

for _, row in df.iterrows():
    if row["recipient"] != user:
        continue

    st.subheader(f"Capsule #{row['id']}")

    if today < pd.to_datetime(row["unlock_date"]).date():
        st.info(f"🔒 Locked until {row['unlock_date']}")
        continue

    pw = st.text_input(
        f"Enter password for Capsule #{row['id']}",
        type="password",
        key=f"pw_{row['id']}"
    )

    if pw and check_password(pw, row["password_hash"]):
        st.success(f"Unlocked on {row['unlock_date']}")
        st.write(row["text"])

        if row["image"]:
            st.image(row["image"])

# ------------------ EDIT CAPSULES ------------------
st.header("Edit Capsules You Created")

for idx, row in df.iterrows():
    if row["creator"] != user:
        continue

    st.subheader(f"Capsule #{row['id']} (Edits left: {MAX_EDITS - row['edit_count']})")

    if row["edit_count"] >= MAX_EDITS:
        st.warning("Edit limit reached. Admin approval required.")
        continue

    new_text = st.text_area(
        "Edit message",
        row["text"],
        key=f"edit_{row['id']}"
    )

    if st.button(f"Save Edit #{row['id']}"):
        df.at[idx, "text"] = new_text
        df.at[idx, "edit_count"] += 1
        save_data(df)
        st.success("Edit saved!")

# ------------------ ADMIN PANEL ------------------
st.header("Admin Panel")

admin_pw = st.text_input("Admin Password", type="password")

if admin_pw == ADMIN_PASSWORD:
    st.success("Admin access granted")

    for idx, row in df.iterrows():
        st.write(f"Capsule #{row['id']} | Edits used: {row['edit_count']}")
        if st.button(f"Allow extra edit for Capsule #{row['id']}"):
            df.at[idx, "edit_count"] = MAX_EDITS - 1
            save_data(df)
            st.success("Extra edit allowed")
