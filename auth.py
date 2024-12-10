import streamlit as st
from utils import create_user, verify_user


def render_auth_ui(db):
    """Renders the authentication UI and handles login/registration logic."""
    st.title("Login")

    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        login_email = st.text_input("Email", key="login_email_field")
        login_password = st.text_input(
            "Password", type="password", key="login_password_field")

        if st.button("Login", key="login_button"):
            provider_id = verify_user(login_email, login_password, db)
            if provider_id:
                st.session_state.authenticated = True
                st.session_state.provider_id = provider_id
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Invalid email or password")

    with tab2:
        new_email = st.text_input("Email", key="register_email")
        new_password = st.text_input(
            "Password", type="password", key="register_password")
        confirm_password = st.text_input("Confirm Password", type="password")

        if st.button("Register"):
            if new_password != confirm_password:
                st.error("Passwords do not match")
            elif not new_email or not new_password:
                st.error("Please fill in all fields")
            else:
                success, message = create_user(new_email, new_password, db)
                if success:
                    st.success(message)
                else:
                    st.error(message)
