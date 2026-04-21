import streamlit as st
import sqlite3
import requests
from datetime import datetime

API_URL = "http://127.0.0.1:8000/analyze"

conn = sqlite3.connect("mental_health.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    input TEXT,
    prediction TEXT,
    confidence REAL,
    response TEXT,
    status TEXT,
    timestamp TEXT
)
""")
conn.commit()


def process_input(user_text):
    try:
        response = requests.post(
            API_URL,
            json={"text": user_text},
            timeout=60
        )
        return response.json()
    except Exception as e:
        return {
            "prediction": "System Error",
            "confidence": 0.0,
            "advice": f"API connection failed: {str(e)}"
        }
def save_case(input_text, prediction, confidence, response):
    c.execute("""
    INSERT INTO cases (input, prediction, confidence, response, status, timestamp)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        input_text,
        prediction,
        confidence,
        response,
        "pending",
        str(datetime.now())
    ))
    conn.commit()


def update_status(case_id, status, new_response=None):
    if new_response:
        c.execute(
            "UPDATE cases SET status=?, response=? WHERE id=?",
            (status, new_response, case_id)
        )
    else:
        c.execute(
            "UPDATE cases SET status=? WHERE id=?",
            (status, case_id)
        )

    conn.commit()


mode = st.sidebar.selectbox(
    "Select Mode",
    ["User", "Psychologist"]
)
if mode == "User":

    st.title("🧠 AI Counselling for Pre-Adults")

    user_input = st.text_area(
        "How are you feeling today?"
    )

    if st.button("Submit") and user_input:

        with st.spinner("Analyzing..."):
            result = process_input(user_input)

        prediction = result["prediction"]
        confidence = result["confidence"]
        advice = result["advice"]

        save_case(
            user_input,
            prediction,
            confidence,
            advice
        )

        st.success("Your request has been submitted for review.")

        st.info("A qualified reviewer will validate the response before it is shown.")


    st.subheader("📬 Approved Responses")

    c.execute("""
    SELECT input, response, timestamp
    FROM cases
    WHERE status='approved'
    ORDER BY id DESC
    LIMIT 5
    """)

    rows = c.fetchall()

    for row in rows:
        st.write(f"📝 {row[0]}")
        st.success(row[1])
        st.caption(row[2])
        st.markdown("---")
if mode == "Psychologist":

    st.title("🧑‍⚕️ Psychologist Validation Dashboard")

    c.execute("""
    SELECT * FROM cases
    WHERE status='pending'
    """)

    cases = c.fetchall()

    if not cases:
        st.info("No pending cases.")

    else:
        for case in cases:

            case_id, text, pred, conf, response_text, status, time = case

            st.write(f"### Case ID: {case_id}")
            st.write(f"Input: {text}")
            st.write(f"Prediction: {pred}")
            st.write(f"Confidence: {conf}")
            st.write(f"AI Response: {response_text}")

            new_response = st.text_area(
                f"Edit Response {case_id}",
                value=response_text,
                key=f"edit_{case_id}"
            )

            col1, col2 = st.columns(2)

            if col1.button(
                f"Approve {case_id}",
                key=f"approve_{case_id}"
            ):
                update_status(
                    case_id,
                    "approved",
                    new_response
                )
                st.success("Approved")

            if col2.button(
                f"Reject {case_id}",
                key=f"reject_{case_id}"
            ):
                update_status(
                    case_id,
                    "rejected"
                )
                st.error("Rejected")

            st.markdown("---")

    st.subheader("📊 Metrics")

    c.execute("SELECT COUNT(*) FROM cases")
    total = c.fetchone()[0]

    c.execute("""
    SELECT COUNT(*) FROM cases
    WHERE status='approved'
    """)
    approved = c.fetchone()[0]

    c.execute("""
    SELECT COUNT(*) FROM cases
    WHERE status='rejected'
    """)
    rejected = c.fetchone()[0]

    pending = total - approved - rejected

    st.metric("Total Cases", total)
    st.metric("Approved", approved)
    st.metric("Rejected", rejected)
    st.metric("Pending", pending)
