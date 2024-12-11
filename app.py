import streamlit as st
from stt import deepgram_stt
from dotenv import load_dotenv
import os
import openai
from audio import AudioRecorder
from data import DatabaseManager
from auth import render_auth_ui
from ui_components import (
    render_sidebar,
    render_visit_records,
    render_patient_notes
)
from utils import get_summary

load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
    st.session_state['provider_id'] = None
    st.session_state['current_file'] = None

# Initialize database connection
db_manager = DatabaseManager()
if db_manager.client:
    db = db_manager.db
else:
    st.error("Failed to initialize MongoDB connection")
    st.stop()


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

    except Exception as e:
        st.error(f"Error processing recording: {str(e)}")
        st.stop()



# Authentication UI
if not st.session_state.authenticated:
    render_auth_ui(db)
    st.stop()

# Main app UI
st.title("Scribe")

# Render sidebar
render_sidebar(db_manager)

# Main content area
if st.session_state.selected_patient:
    st.header(
        f"{st.session_state.first_name} {st.session_state.last_name}".title())

    # Render patient notes section
    render_patient_notes(db_manager)

    # Recording session
    st.header("Recording Session")

    transcript = deepgram_stt(deepgram_api_key=os.getenv(
        'DEEPGRAM_API_KEY'))

    if transcript:
        process_new_recording(transcript)
        transcript = None


    # Render visit records
    render_visit_records(db_manager)
else:
    st.info("Please select a patient from the sidebar")
