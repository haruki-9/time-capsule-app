import streamlit as st
import pandas as pd
import os
import hashlib
import re
from datetime import date

# ---------------- CONFIG ----------------
USER_FILE = "users.csv"
CAPSULE_FILE = "capsules.csv"
IMAGE_DIR = "images"

os.makedirs(IMAGE_DIR, exist_ok=True)

# ---------------- HELPERS ----------------
def hash_text(text):
    return hashlib.sha256(text.encode()).hexdigest()

def valid_password(pw):
    return bool(re.fullmatch(r"[A-Za-z0-9]+", pw))

def load_users():
    if not os.path.exists(USER_FILE):
        return pd.DataFrame(columns=["username", "password_hash"])
    return pd.read_csv(USER_FILE)

def save_users(df):
    df.to_csv(USER_FILE, index=False)

def load_capsules():
    if not os.path.exists(CAPSULE_FILE):
        return pd.DataFrame(columns=[
            "id", "creator", "recipient",
            "message", "image", "unlock_date",
            "capsule_pw_hash"
        ])
    return pd.read_csv(CAPSULE_FILE)

def save_capsules(df):
    df.to_csv(CAPSULE_FILE, index=False)

# ---------------- SESSION ----------------
if "user" not in st.session_state:
    st.session_state.user = None

# ---------------- TITLE ----------------
st.title("⏳ Time Capsule")

users_df = load_users()

# ======================================================
# LOGIN / SIGNUP (SMART, NO DROPDOWN)
# ======================================================
if st.session_state.user is None:
    st.subheader("Login or Create Account")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    st.caption("Password must contain only letters and numbers")

    if st.button("Continue"):
        if not username or not password:
            st.error("Username and password required")
            st.stop()

        if not valid_password(password):
            st.error("Password must contain only letters and numbers")
            st.stop()

        existing = users_df[users_df["username"] == username]

        # ---------- LOGIN ----------
        if not existing.empty:
            stored_hash = existing.iloc[0]["password_hash"]
            if hash_text(password) == stored_hash:
                st.session_state.user = username
                st.success("Login successful")
                st.rerun()
            else:
                st.error("Incorrect password")

        # ---------- SIGN UP ----------
        else:
            users_df = pd.concat([
                users_df,
                pd.DataFrame([{
                    "username": username,
                    "password_hash": hash_text(password)
                }])
            ], ignore_index=True)

            save_users(users_df)
            st.session_state.user = username
            st.success("Account created successfully")
            st.rerun()

    st.stop()

# ======================================================
# DASHBOARD
# ======================================================
user = st.session_state.user
st.success(f"Welcome, {user}")

capsules_df = load_capsules()
today = date.today()

menu = st.radio(
    "Choose an option",
    ["Create Capsule", "View Capsules Received", "View Capsules You Created"]
)

# ---------------- CREATE CAPSULE ----------------
if menu == "Create Capsule":
    st.header("📦 Create a Time Capsule")

    recipients = users_df["username"].tolist()

    with st.form("create_capsule"):
        recipient = st.text_input("Send to (username)")
        unlock_date = st.date_input("Unlock date", min_value=today)
        capsule_pw = st.text_input("Capsule password", type="password")
        message = st.text_area("Message")
        image = st.file_uploader("Optional image", ["jpg", "png", "jpeg"])

        submit = st.form_submit_button("Create")

        if submit:
            if not recipient or not message or not capsule_pw:
                st.error("All fields except image are required")
            elif not valid_password(capsule_pw):
                st.error("Capsule password must be letters and numbers only")
            else:
                cid = len(capsules_df) + 1
                img_path = ""

                if image:
                    img_path = f"{IMAGE_DIR}/{cid}_{image.name}"
                    with open(img_path, "wb") as f:
                        f.write(image.read())

                capsules_df = pd.concat([
                    capsules_df,
                    pd.DataFrame([{
                        "id": cid,
                        "creator": user,
                        "recipient": recipient,
                        "message": message,
                        "image": img_path,
                        "unlock_date": unlock_date,
                        "capsule_pw_hash": hash_text(capsule_pw)
                    }])
                ], ignore_index=True)

                save_capsules(capsules_df)
                st.success("Capsule created")

# ---------------- VIEW RECEIVED ----------------
elif menu == "View Capsules Received":
    st.header("📬 Capsules Sent To You")

    found = False
    for _, row in capsules_df.iterrows():
        if row["recipient"] != user:
            continue

        found = True
        st.subheader(f"Capsule #{row['id']} from {row['creator']}")

        unlock = pd.to_datetime(row["unlock_date"]).date()
        if today < unlock:
            st.info(f"🔒 Locked until {unlock}")
            continue

        pw = st.text_input(
            "Capsule password",
            type="password",
            key=f"cap_{row['id']}"
        )

        if pw and hash_text(pw) == row["capsule_pw_hash"]:
            st.success("Unlocked")
            st.write(row["message"])
            if row["image"]:
                st.image(row["image"])

    if not found:
        st.info("No capsules yet")

# ---------------- VIEW CREATED ----------------
elif menu == "View Capsules You Created":
    st.header("📝 Capsules You Created")

    found = False
    for _, row in capsules_df.iterrows():
        if row["creator"] != user:
            continue

        found = True
        st.subheader(f"Capsule #{row['id']} → {row['recipient']}")
        st.write(f"Unlock date: {row['unlock_date']}")
        st.write(row["message"])
        if row["image"]:
            st.image(row["image"])

    if not found:
        st.info("You haven't created any capsules")

# ---------------- LOGOUT ----------------
st.divider()
if st.button("Logout"):
    st.session_state.user = None
    st.rerun()
