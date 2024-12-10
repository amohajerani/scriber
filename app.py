import streamlit as st
from whisper_stt import whisper_stt
from dotenv import load_dotenv
import os
import openai
import json
from datetime import datetime
import re
from streamlit.components.v1 import html
import pyperclip
import ssl
import hashlib
import hmac
from data import DatabaseManager
from user_utils import create_user, verify_user

load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
    st.session_state['provider_id'] = None

# Initialize database connection
db_manager = DatabaseManager()
if db_manager.client:
    db = db_manager.db
else:
    st.error("Failed to initialize MongoDB connection")
    st.stop()

first_name = ""
last_name = ""


def get_summary(transcript, system_prompt):
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": transcript}
        ]
    )
    return response.choices[0].message.content


def split_patient_name(combined_name):
    parts = re.split(r'[- ]', combined_name)
    if len(parts) >= 2:
        return parts[0], ' '.join(parts[1:])
    return combined_name, ""


def create_copy_button(text, button_id):
    escaped_text = text.replace('`', '\\`').replace(
        '\\', '\\\\').replace('\n', '\\n')
    copy_js = f"""
        <script>
        function copyText{button_id}() {{
            const text = `{escaped_text}`;
            navigator.clipboard.writeText(text).then(function() {{
                console.log('Text copied');
            }}).catch(function(err) {{
                console.error('Failed to copy text:', err);
            }});
        }}
        </script>
        <button 
            onclick="copyText{button_id}()"
            style="background-color: transparent; border: none; padding: 0; margin-left: 5px; cursor: pointer; font-size: 20px;"
        >
            🔗
        </button>
    """
    return copy_js


def process_new_recording(transcript):
    try:
        with st.spinner('Generating summary...'):
            system_prompt = st.session_state.current_prompt
            summary = get_summary(transcript, system_prompt)
            doc_id = db_manager.save_recording_data(
                transcript,
                summary,
                st.session_state.provider_id,
                st.session_state.selected_patient_id
            )
            st.session_state.current_file = doc_id
            st.success("Recording saved successfully!")
            st.rerun()
    except Exception as e:
        st.error(f"Error processing recording: {str(e)}")
        st.stop()


# Authentication UI
if not st.session_state.authenticated:
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

    st.stop()

# Main app UI
st.title("Scribe")

# Sidebar for patient selection
with st.sidebar:
    if st.button("Logout"):
        st.session_state.authenticated = False
        st.rerun()

    st.divider()
    st.header("Patient Selection")
    patients = db_manager.get_all_patients(st.session_state.provider_id)

    if 'selected_patient' not in st.session_state:
        st.session_state.selected_patient = ""
        st.session_state.first_name = ""
        st.session_state.last_name = ""

    if patients:
        patient_options = [""] + [f"{p[0]} {p[1]}" for p in patients]
        patient_ids = {f"{p[0]} {p[1]}": p[2] for p in patients}

        selected_patient = st.selectbox(
            "Select Existing Patient",
            options=patient_options,
            format_func=lambda x: "Select a patient..." if x == "" else x,
            index=patient_options.index(
                st.session_state.selected_patient) if st.session_state.selected_patient in patient_options else 0
        )

        st.session_state.selected_patient = selected_patient

        if selected_patient:
            first_name, last_name = split_patient_name(selected_patient)
            st.session_state.first_name = first_name
            st.session_state.last_name = last_name
            st.session_state.selected_patient_id = patient_ids.get(
                selected_patient)
            if 'notes' in st.session_state:
                del st.session_state.notes
        else:
            st.session_state.first_name = ""
            st.session_state.last_name = ""
            st.session_state.selected_patient_id = None
            if 'notes' in st.session_state:
                del st.session_state.notes

        st.divider()

    st.subheader("Or Create New patient")
    new_first_name = st.text_input("First Name")
    new_last_name = st.text_input("Last Name")

    if st.button("Create New patient"):
        if new_first_name and new_last_name:
            formatted_first_name = new_first_name.capitalize()
            formatted_last_name = new_last_name.capitalize()

            try:
                patient_id = db_manager.save_patient_data(
                    formatted_first_name,
                    formatted_last_name,
                    st.session_state.provider_id
                )
                st.success(
                    f"Created new patient: {formatted_first_name} {formatted_last_name}")
                st.session_state.selected_patient = f"{formatted_first_name} {formatted_last_name}"
                st.session_state.first_name = formatted_first_name
                st.session_state.last_name = formatted_last_name
                st.rerun()
            except Exception as e:
                st.error(f"Error saving patient to database: {str(e)}")
        else:
            st.error("Please enter both first and last name")

    st.divider()
    with st.expander("Select System Prompt", expanded=False):
        system_prompts = db_manager.load_system_prompts(
            st.session_state.provider_id)

        selected_prompt_name = st.selectbox(
            "Select a prompt template:",
            options=list(system_prompts.keys())
        )

        updated_prompt = st.text_area(
            "Customize the selected prompt:",
            value=system_prompts[selected_prompt_name],
            height=150
        )

        st.session_state.current_prompt = updated_prompt

        if updated_prompt != system_prompts[selected_prompt_name]:
            system_prompts[selected_prompt_name] = updated_prompt
            db_manager.save_system_prompts(
                system_prompts, st.session_state.provider_id)
            st.success("Prompt updated successfully!")

        new_prompt_name = st.text_input("New prompt name")
        if st.button("Add New Prompt"):
            if new_prompt_name:
                if new_prompt_name in system_prompts:
                    st.error("A prompt with this name already exists!")
                else:
                    system_prompts[new_prompt_name] = "Enter your prompt here"
                    db_manager.save_system_prompts(
                        system_prompts, st.session_state.provider_id)
                    st.success("New prompt template added!")
                    st.rerun()

    with st.sidebar:
        st.divider()
        st.markdown("**Current Prompt Template:**")
        st.info(selected_prompt_name)

# Main content area
if st.session_state.selected_patient:
    st.header(
        f"{st.session_state.first_name} {st.session_state.last_name}".title())

    if 'notes' not in st.session_state:
        st.session_state.notes = db_manager.get_patient_notes(
            st.session_state.selected_patient_id)

    st.subheader("Notes")
    notes = st.text_area("Enter your notes here:",
                         value=st.session_state.notes,
                         height=150)

    if st.button("Save Notes"):
        db_manager.update_patient_notes(
            st.session_state.selected_patient_id, notes)
        st.session_state.notes = notes
        st.success("Notes saved successfully!")

    st.header("Recording Session")
    transcript = whisper_stt(openai_api_key=os.getenv(
        'OPENAI_API_KEY'), language='en')

    if transcript:
        if 'last_transcript' not in st.session_state or transcript != st.session_state.last_transcript:
            st.session_state.last_transcript = transcript
            process_new_recording(transcript)

        if st.session_state.current_file:
            saved_data = db_manager.load_recording_data(
                st.session_state.current_file)

            col1, col2 = st.columns(2)

            with col1:
                header_col1, header_col2 = st.columns([0.8, 0.2])
                with header_col1:
                    st.subheader("Transcript")
                with header_col2:
                    st.write("")
                    if st.button("🔗", key=f"copy_transcript_{saved_data['transcript'][:10]}", use_container_width=False):
                        pyperclip.copy(saved_data["transcript"])
                        st.toast('Copied to clipboard!')

                edited_transcript = st.text_area(
                    label="Transcript content",
                    label_visibility="hidden",
                    value=saved_data["transcript"],
                    height=300,
                    key="current_transcript"
                )

            with col2:
                header_col1, header_col2, header_col3 = st.columns(
                    [0.6, 0.2, 0.2])
                with header_col1:
                    st.subheader("Summary")
                with header_col2:
                    st.write("")
                    if st.button("🔗", key=f"copy_summary_current_{saved_data['summary'][:10]}", use_container_width=False):
                        pyperclip.copy(saved_data["summary"])
                        st.toast('Copied to clipboard!')
                with header_col3:
                    if st.button("🔄", key=f"regenerate_summary_current", use_container_width=False):
                        with st.spinner('Generating new summary...'):
                            new_summary = get_summary(
                                edited_transcript,
                                st.session_state.current_prompt
                            )
                            db_manager.update_recording_data(
                                st.session_state.current_file,
                                edited_transcript,
                                new_summary
                            )
                            st.success("Summary regenerated successfully!")
                            st.rerun()

                edited_summary = st.text_area(
                    label="Summary content",
                    label_visibility="hidden",
                    value=saved_data["summary"],
                    height=300,
                    key="current_summary"
                )

            if st.button("Save Changes", key="save_current_btn"):
                db_manager.update_recording_data(
                    st.session_state.current_file,
                    edited_transcript,
                    edited_summary
                )
                st.success("Changes saved successfully!")

    st.header("Visit Records")
    recordings = db_manager.get_patient_recordings(
        st.session_state.selected_patient_id,
        st.session_state.provider_id
    )

    if recordings:
        recording_options = [
            (r["timestamp"].strftime("%Y-%m-%d %H:%M"), str(r["_id"]))
            for r in recordings
        ]

        selected_recording = st.selectbox(
            "Select a recording:",
            options=[r[1] for r in recording_options],
            format_func=lambda x: next(r[0]
                                       for r in recording_options if r[1] == x),
            key="visit_recording_selector"
        )

        if selected_recording:
            data = db_manager.load_recording_data(selected_recording)
            formatted_date = data['last_modified'].strftime("%Y-%m-%d %H:%M")

            col1, col2 = st.columns(2)

            with col1:
                header_col1, header_col2 = st.columns([0.8, 0.2])
                with header_col1:
                    st.subheader("Transcript")
                with header_col2:
                    if st.button("🔗", key=f"copy_transcript_{selected_recording}", use_container_width=False):
                        pyperclip.copy(data["transcript"])
                        st.toast('Copied to clipboard!')

                edited_transcript = st.text_area(
                    label="Transcript content",
                    label_visibility="hidden",
                    value=data["transcript"],
                    height=300,
                    key="transcript"
                )

            with col2:
                header_col1, header_col2, header_col3 = st.columns(
                    [0.6, 0.2, 0.2])
                with header_col1:
                    st.subheader("Summary")
                with header_col2:
                    if st.button("🔗", key=f"copy_summary_{selected_recording}", use_container_width=False):
                        pyperclip.copy(data["summary"])
                        st.toast('Copied to clipboard!')
                with header_col3:
                    if st.button("🔄", key=f"regenerate_summary_{selected_recording}", use_container_width=False):
                        with st.spinner('Generating new summary...'):
                            new_summary = get_summary(
                                edited_transcript,
                                st.session_state.current_prompt
                            )
                            db_manager.update_recording_data(
                                selected_recording,
                                edited_transcript,
                                new_summary
                            )
                            st.success("Summary regenerated successfully!")
                            st.rerun()

                edited_summary = st.text_area(
                    label="Summary content",
                    label_visibility="hidden",
                    value=data["summary"],
                    height=300,
                    key="summary"
                )

            st.markdown(f"**Last Updated:** {formatted_date}")

            if st.button("Save Changes", key="save_changes"):
                db_manager.update_recording_data(
                    selected_recording,
                    edited_transcript,
                    edited_summary
                )
                st.success("Changes saved successfully!")
    else:
        st.info("No recordings found for this patient")
else:
    st.info("Please select a patient from the sidebar")
