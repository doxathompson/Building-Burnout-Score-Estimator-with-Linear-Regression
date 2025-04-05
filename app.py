import streamlit as st
import pandas as pd
import numpy as np
import joblib
from PIL import Image
import matplotlib.pyplot as plt
import sqlite3
import hashlib
from datetime import datetime

# Load model
model = joblib.load('burnout_model.pkl')

# Database functions for user authentication
def create_connection():
    conn = sqlite3.connect('burnout_users.db', check_same_thread=False)
    return conn

def create_users_table():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def create_user_history_table():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            work_hours_per_day REAL,
            sleep_hours REAL,
            exercise_minutes REAL,
            social_hours REAL,
            screen_time_nonwork REAL,
            breaks_per_day REAL,
            coffee_cups INTEGER,
            stress_level INTEGER,
            burnout_score REAL,
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    conn.commit()
    conn.close()

def add_user(username, password):
    conn = create_connection()
    cursor = conn.cursor()
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    try:
        cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def verify_user(username, password):
    conn = create_connection()
    cursor = conn.cursor()
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    cursor.execute('SELECT id FROM users WHERE username = ? AND password = ?', (username, hashed_password))
    user = cursor.fetchone()
    conn.close()
    return user[0] if user else None

def save_user_history(user_id, inputs, score):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO user_history (
            user_id, work_hours_per_day, sleep_hours, exercise_minutes,
            social_hours, screen_time_nonwork, breaks_per_day, coffee_cups,
            stress_level, burnout_score
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, *inputs.values(), score))
    conn.commit()
    conn.close()

def get_user_history(user_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT recorded_at, burnout_score FROM user_history 
        WHERE user_id = ? ORDER BY recorded_at
    ''', (user_id,))
    history = cursor.fetchall()
    conn.close()
    return history

# Initialize database
create_users_table()
create_user_history_table()

# Burnout meter image function
def create_burnout_meter(score):
    fig, ax = plt.subplots(figsize=(8, 2))
    ax.barh(['Burnout Level'], [100], color='#f0f0f0')
    ax.barh(['Burnout Level'], [score], color='#ff6b6b')
    
    # Add zones
    ax.axvline(x=30, color='green', linestyle='--', linewidth=1)
    ax.axvline(x=70, color='orange', linestyle='--', linewidth=1)
    
    # Add text labels
    ax.text(15, -0.3, 'Low', ha='center', color='green')
    ax.text(50, -0.3, 'Moderate', ha='center', color='orange')
    ax.text(85, -0.3, 'High', ha='center', color='red')
    
    ax.set_xlim(0, 100)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(f'Your Burnout Score: {score:.1f}/100', pad=20)
    
    return fig


# Added this to Enhanced Visualization
def create_burnout_meter(score):
    fig, ax = plt.subplots(figsize=(10, 2))
    # Gradient background
    ax.imshow(np.linspace(0, 1, 100).reshape(1, -1), 
             cmap='RdYlGn_r', aspect='auto',
             extent=[0, 100, 0, 1])
    # Score indicator
    ax.plot([score, score], [0, 1], color='black', linewidth=3)
    ax.text(score, 1.1, f'{score:.0f}', ha='center', fontsize=12)
    # Styling
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 1)
    ax.axis('off')
    return fig


# Recommendations based on score
def get_recommendations(score):
    if score < 30:
        return [
            "You're doing great! Maintain your healthy habits.",
            "Consider sharing your work-life balance strategies with colleagues."
        ]
    elif score < 70:
        return [
            "You're doing okay, but could use some improvements.",
            "Try to take more breaks during work hours.",
            "Consider reducing screen time in the evenings."
        ]
    else:
        return [
            "⚠️ Warning: You're at high risk of burnout!",
            "Prioritize taking time off if possible.",
            "Schedule a meeting with your manager to discuss workload.",
            "Make sure you're getting enough quality sleep.",
            "Try to incorporate short walks during your day."
        ]

# Main app
def main():
    st.set_page_config(page_title="Burnout Score Estimator", page_icon="🔥", layout="wide")
    
    # Initialize session state
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.session_state.username = None
    
    # Login/Signup sidebar
    with st.sidebar:
        st.title("Account")
        
        if st.session_state.logged_in:
            st.success(f"Logged in as {st.session_state.username}")
            if st.button("Logout"):
                st.session_state.logged_in = False
                st.session_state.user_id = None
                st.session_state.username = None
                st.rerun()
            
            # Show history
            st.subheader("Your History")
            history = get_user_history(st.session_state.user_id)
            if history:
                dates = [h[0] for h in history]
                scores = [h[1] for h in history]
                fig, ax = plt.subplots()
                ax.plot(dates, scores, marker='o')
                ax.set_title("Your Burnout Score Over Time")
                ax.set_ylim(0, 100)
                ax.set_ylabel("Burnout Score")
                plt.xticks(rotation=45)
                st.pyplot(fig)
            else:
                st.info("No history yet. Complete an assessment to track your progress.")
        else:
            tab1, tab2 = st.tabs(["Login", "Sign Up"])
            
            with tab1:
                username = st.text_input("Username", key="login_username")
                password = st.text_input("Password", type="password", key="login_password")
                if st.button("Login"):
                    user_id = verify_user(username, password)
                    if user_id:
                        st.session_state.logged_in = True
                        st.session_state.user_id = user_id
                        st.session_state.username = username
                        st.rerun()
                    else:
                        st.error("Invalid username or password")
            
            with tab2:
                new_username = st.text_input("Username", key="signup_username")
                new_password = st.text_input("Password", type="password", key="signup_password")
                confirm_password = st.text_input("Confirm Password", type="password")
                
                if st.button("Create Account"):
                    if new_password != confirm_password:
                        st.error("Passwords don't match")
                    elif len(new_password) < 6:
                        st.error("Password must be at least 6 characters")
                    else:
                        if add_user(new_username, new_password):
                            st.success("Account created! Please log in.")
                        else:
                            st.error("Username already exists")
    
    # Main content
    st.title("🔥 Burnout Score Estimator")
    st.markdown("""
        This tool estimates your risk of burnout based on your daily habits and work patterns.
        Complete the form below to get your personalized burnout score and recommendations.
    """)
    
    with st.form("burnout_form"):
        st.subheader("Your Daily Habits")
        
        col1, col2 = st.columns(2)
        
        with col1:
            work_hours = st.slider("Work hours per day", 4, 12, 8)
            sleep_hours = st.slider("Sleep hours", 4, 10, 7)
            exercise_minutes = st.slider("Exercise minutes", 0, 120, 30)
            social_hours = st.slider("Social/family time (hours)", 0, 6, 2)
        
        with col2:
            screen_time = st.slider("Non-work screen time (hours)", 1, 8, 4)
            breaks = st.slider("Breaks taken during work", 0, 10, 5)
            coffee_cups = st.slider("Cups of coffee/tea", 0, 6, 2)
            stress_level = st.slider("Perceived stress level (1-5)", 1, 5, 3)
        
        submitted = st.form_submit_button("Calculate Burnout Score")
        
        if submitted:
            # Prepare input data
            input_data = {
                'work_hours_per_day': work_hours,
                'sleep_hours': sleep_hours,
                'exercise_minutes': exercise_minutes,
                'social_hours': social_hours,
                'screen_time_nonwork': screen_time,
                'breaks_per_day': breaks,
                'coffee_cups': coffee_cups,
                'stress_level': stress_level
            }
            
            # Convert to DataFrame for prediction
            input_df = pd.DataFrame([input_data])
            
            # Predict
            burnout_score = model.predict(input_df)[0]
            burnout_score = max(0, min(100, burnout_score))  # Ensure within 0-100 range
            
            # Display results
            st.subheader("Results")
            
            # Burnout meter
            fig = create_burnout_meter(burnout_score)
            st.pyplot(fig)
            
            # Recommendations
            st.subheader("Recommendations")
            for rec in get_recommendations(burnout_score):
                st.write(f"- {rec}")
            
            # Save to history if logged in
            if st.session_state.logged_in:
                save_user_history(st.session_state.user_id, input_data, burnout_score)
                st.success("Results saved to your history")

if __name__ == "__main__":
    main()