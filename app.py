# Import required libraries
import streamlit as st
import pandas as pd
import numpy as np
import joblib
import matplotlib.pyplot as plt
import sqlite3
import hashlib
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
from contextlib import closing
import os

# ==============================================
# PRODUCTION DATABASE FUNCTIONS
# ==============================================

def create_connection():
    """Create and return a connection to the SQLite database"""
    return sqlite3.connect('burnout_users.db', check_same_thread=False)

def migrate_database():
    """
    Safely updates database schema without data loss.
    Runs only when needed.
    """
    try:
        with closing(create_connection()) as conn:
            cursor = conn.cursor()
            
            # Create tables if they don't exist
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL DEFAULT 'unknown@example.com',
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            cursor.execute("""
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
            """)
            
            # Check and add missing columns
            cursor.execute("PRAGMA table_info(users)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'email' not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN email TEXT DEFAULT 'unknown@example.com'")
            
            conn.commit()
            
    except Exception as e:
        st.error("Database maintenance in progress. Please try again later.")
        raise

def add_user(username, email, password):
    """Add a new user to the database"""
    try:
        with closing(create_connection()) as conn:
            cursor = conn.cursor()
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            cursor.execute(
                'INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                (username, email, hashed_password)
            )
            conn.commit()
            return True
    except sqlite3.IntegrityError:
        return False

def verify_user(username, password):
    """Verify user credentials"""
    try:
        with closing(create_connection()) as conn:
            cursor = conn.cursor()
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            cursor.execute(
                'SELECT id, email FROM users WHERE username = ? AND password = ?',
                (username, hashed_password)
            )
            user = cursor.fetchone()
            return user if user else None
    except Exception as e:
        st.error("Login service temporarily unavailable")
        return None

def save_user_history(user_id, inputs, score):
    """Save user assessment to history"""
    try:
        with closing(create_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO user_history (
                    user_id, work_hours_per_day, sleep_hours, exercise_minutes,
                    social_hours, screen_time_nonwork, breaks_per_day, coffee_cups,
                    stress_level, burnout_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, *inputs.values(), score))
            conn.commit()
    except Exception as e:
        st.error("Could not save your results. Please try again.")

def get_user_history(user_id):
    """Get user's assessment history"""
    try:
        with closing(create_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT recorded_at, burnout_score FROM user_history 
                WHERE user_id = ? ORDER BY recorded_at
            ''', (user_id,))
            return cursor.fetchall()
    except Exception as e:
        st.error("Could not load your history")
        return []

# ==============================================
# UTILITY FUNCTIONS
# ==============================================

def validate_password(password):
    """Validate password meets requirements"""
    if len(password) < 8:
        return "Password must be at least 8 characters"
    if not any(c.isupper() for c in password):
        return "Password must contain at least one uppercase letter"
    if not any(c.isdigit() for c in password):
        return "Password must contain at least one digit"
    return None

def validate_inputs(inputs):
    """Validate form inputs"""
    errors = []
    if inputs['work_hours_per_day'] > 16:
        errors.append("Work hours cannot exceed 16 per day")
    if inputs['sleep_hours'] < 4:
        errors.append("Sleep hours should be at least 4")
    elif inputs['sleep_hours'] > 12:
        errors.append("Sleep hours cannot exceed 12")
    if not 1 <= inputs['stress_level'] <= 5:
        errors.append("Stress level must be between 1-5")
    return errors

def create_burnout_meter(score):
    """Create a visual burnout meter"""
    fig, ax = plt.subplots(figsize=(10, 2))
    
    # Gradient background
    gradient = np.linspace(0, 1, 100).reshape(1, -1)
    ax.imshow(gradient, aspect='auto', cmap='RdYlGn_r', extent=[0, 100, 0, 1])
    
    # Score indicator
    ax.plot([score, score], [0, 1], color='black', linewidth=3)
    ax.scatter([score], [0.5], color='black', s=200, zorder=5)
    
    # Score text
    ax.text(score, 1.2, f'{score:.0f}', ha='center', va='center', 
           fontsize=14, weight='bold', bbox=dict(facecolor='white', alpha=0.8))
    
    # Zone labels
    for x, label in [(20, 'Low'), (50, 'Medium'), (80, 'High')]:
        ax.text(x, 0.5, label, ha='center', va='center', 
               color='white' if x > 40 else 'black', weight='bold')
    
    # Styling
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 1)
    ax.axis('off')
    plt.tight_layout()
    
    return fig

def get_recommendations(score):
    """Generate personalized recommendations"""
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

def send_email(to_email, subject, body):
    """Send email notification using environment variables"""
    try:
        smtp_server = os.getenv("SMTP_SERVER")
        smtp_port = int(os.getenv("SMTP_PORT", 587))
        smtp_username = os.getenv("SMTP_USERNAME")
        smtp_password = os.getenv("SMTP_PASSWORD")
        from_email = os.getenv("FROM_EMAIL", smtp_username)
        
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = from_email
        msg['To'] = to_email
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
        return True
    except Exception as e:
        st.error("Email service temporarily unavailable")
        return False

# ==============================================
# MAIN APPLICATION
# ==============================================

def main():
    # Configure page settings
    st.set_page_config(
        page_title="Burnout Score Estimator", 
        page_icon="🔥", 
        layout="wide"
    )
    
    # Initialize database safely
    migrate_database()
    
    # Initialize session state
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.session_state.username = None
        st.session_state.email = None
    
    # ==========================================
    # SIDEBAR - USER AUTHENTICATION
    # ==========================================
    with st.sidebar:
        st.title("Account")
        
        if st.session_state.logged_in:
            st.success(f"Logged in as {st.session_state.username}")
            
            if st.button("Logout"):
                st.session_state.logged_in = False
                st.session_state.user_id = None
                st.session_state.username = None
                st.session_state.email = None
                st.rerun()
            
            st.subheader("Your History")
            history = get_user_history(st.session_state.user_id)
            if history:
                dates = [h[0] for h in history]
                scores = [h[1] for h in history]
                
                fig, ax = plt.subplots()
                ax.plot(dates, scores, marker='o', color='#ff6b6b')
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
                    user_data = verify_user(username, password)
                    if user_data:
                        st.session_state.logged_in = True
                        st.session_state.user_id = user_data[0]
                        st.session_state.username = username
                        st.session_state.email = user_data[1]
                        st.rerun()
                    else:
                        st.error("Invalid username or password")
            
            with tab2:
                new_username = st.text_input("Username", key="signup_username")
                new_email = st.text_input("Email", key="signup_email")
                new_password = st.text_input("Password", type="password", key="signup_password")
                confirm_password = st.text_input("Confirm Password", type="password")
                
                if st.button("Create Account"):
                    if new_password != confirm_password:
                        st.error("Passwords don't match")
                    else:
                        password_error = validate_password(new_password)
                        if password_error:
                            st.error(password_error)
                        else:
                            if add_user(new_username, new_email, new_password):
                                st.success("Account created! Please log in.")
                            else:
                                st.error("Username or email already exists")
    
    # ==========================================
    # MAIN CONTENT - BURNOUT ASSESSMENT
    # ==========================================
    st.title("🔥 Burnout Score Estimator")
    st.markdown("""
        This tool estimates your risk of burnout based on your daily habits and work patterns.
        Complete the form below to get your personalized burnout score and recommendations.
    """)
    
    try:
        model = joblib.load('burnout_model.pkl')
    except FileNotFoundError:
        st.error("Service temporarily unavailable. Please try again later.")
        st.stop()
    
    with st.form("burnout_form"):
        st.subheader("Your Daily Habits")
        
        col1, col2 = st.columns(2)
        
        with col1:
            work_hours = st.slider("Work hours per day", 4, 16, 8)
            sleep_hours = st.slider("Sleep hours", 4, 12, 7)
            exercise_minutes = st.slider("Exercise minutes", 0, 120, 30)
            social_hours = st.slider("Social/family time (hours)", 0, 6, 2)
        
        with col2:
            screen_time = st.slider("Non-work screen time (hours)", 1, 8, 4)
            breaks = st.slider("Breaks taken during work", 0, 10, 5)
            coffee_cups = st.slider("Cups of coffee/tea", 0, 6, 2)
            stress_level = st.slider("Perceived stress level (1-5)", 1, 5, 3)
        
        submitted = st.form_submit_button("Calculate Burnout Score")
        
        if submitted:
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
            
            validation_errors = validate_inputs(input_data)
            if validation_errors:
                for error in validation_errors:
                    st.error(error)
            else:
                try:
                    input_df = pd.DataFrame([input_data])
                    burnout_score = model.predict(input_df)[0]
                    burnout_score = max(0, min(100, burnout_score))
                    
                    st.subheader("Results")
                    st.pyplot(create_burnout_meter(burnout_score))
                    
                    st.subheader("Recommendations")
                    for rec in get_recommendations(burnout_score):
                        st.write(f"- {rec}")
                    
                    if st.session_state.logged_in:
                        save_user_history(st.session_state.user_id, input_data, burnout_score)
                        st.success("Results saved to your history")
                        
                        if burnout_score > 70:
                            if st.button("Send results to my email"):
                                body = f"""Your Burnout Score: {burnout_score:.1f}
                                
Recommendations:
{chr(10).join(get_recommendations(burnout_score))}

Track your progress at [your app URL]
"""
                                if send_email(
                                    st.session_state.email, 
                                    "Your Burnout Score Results", 
                                    body
                                ):
                                    st.success("Email sent with your results!")
                except Exception as e:
                    st.error("Service temporarily unavailable. Please try again later.")

if __name__ == "__main__":
    main()