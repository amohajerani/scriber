import streamlit as st
import bcrypt
from typing import Optional


def init_auth_state():
    """Initialize authentication-related session state variables."""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'provider_id' not in st.session_state:
        st.session_state.provider_id = None
    if 'email' not in st.session_state:
        st.session_state.email = None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify if the provided password matches the stored hash."""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


def authenticate_user(email: str, password: str, db) -> Optional[str]:
    """
    Authenticate user against database.
    Returns provider_id if successful, None if authentication fails.
    """
    user = db.get_provider_by_username(email)
    if user and verify_password(password, user['password']):
        return str(user['_id'])
    return None


def handle_login(email: str, password: str, db) -> bool:
    """Handle login attempt and update session state."""
    provider_id = authenticate_user(email, password, db)
    if provider_id:
        st.session_state.authenticated = True
        st.session_state.provider_id = provider_id
        st.session_state.email = email
        return True
    return False


def handle_logout():
    """Handle logout and clear session state."""
    st.session_state.authenticated = False
    st.session_state.provider_id = None
    st.session_state.email = None
    st.session_state.selected_patient = ""
    st.session_state.selected_patient_id = None
    # Clear any other relevant session state variables
    st.rerun()


def show_auth_ui(db):
    """Display authentication UI and handle login/registration logic."""
    if not st.session_state.authenticated:
        st.title("Authentication")

        # Create tabs for login and registration
        login_tab, register_tab = st.tabs(["Login", "Register"])

        # Login tab
        with login_tab:
            with st.form("login_form"):
                email = st.text_input("Email")
                password = st.text_input("Password", type="password")
                submit = st.form_submit_button("Login")

                if submit:
                    if email and password:
                        provider_id = db.verify_user(email, password)
                        if provider_id:
                            st.session_state.authenticated = True
                            st.session_state.provider_id = provider_id
                            st.session_state.email = email
                            st.success("Login successful!")
                            st.rerun()
                        else:
                            st.error("Invalid email or password")
                    else:
                        st.error("Please enter both email and password")

        # Registration tab
        with register_tab:
            with st.form("registration_form"):
                new_email = st.text_input("Email")
                new_password = st.text_input("New Password", type="password")
                confirm_password = st.text_input(
                    "Confirm Password", type="password")
                register = st.form_submit_button("Register")

                if register:
                    if new_password != confirm_password:
                        st.error("Passwords do not match")
                    elif not new_email or not new_password:
                        st.error("Please fill in all fields")
                    else:
                        success, message = db.create_user(
                            new_email, new_password)
                        if success:
                            st.success(
                                "Registration successful! Please login.")
                        else:
                            st.error(message)

        # Stop the app from running further if not authenticated
        st.stop()

    return st.session_state.provider_id
