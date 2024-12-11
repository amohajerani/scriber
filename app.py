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

# Initialize recorder and recording state if not exists
if 'audio_recorder' not in st.session_state:
    st.session_state.audio_recorder = AudioRecorder()
if 'is_recording' not in st.session_state:
    st.session_state.is_recording = False

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

    # Create a button that toggles between Start and Stop
    if not st.session_state.is_recording:
        if st.button("Start Recording"):
            st.session_state.is_recording = True
            st.session_state.audio_recorder.start_recording()
            st.rerun()
    else:
        if st.button("Stop Recording"):
            st.session_state.is_recording = False
            audio = st.session_state.audio_recorder.stop_recording()
            if not audio:
                st.error("No audio data recorded")
                st.stop()

            if audio:
                st.write('audio size: ', len(audio))
                with st.spinner('Transcribing audio...'):
                    transcript = deepgram_stt(audio)

                if transcript:
                    try:
                        with st.spinner('Generating summary...'):
                            summary = get_summary(
                                transcript, st.session_state.current_prompt)
                            doc_id = db_manager.save_recording_data(
                                transcript,
                                summary,
                                st.session_state.provider_id,
                                st.session_state.selected_patient_id
                            )
                            st.success("Recording saved successfully!")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error processing recording: {str(e)}")
                        st.stop()

    # Display current recording status
    if st.session_state.is_recording:
        st.warning("🎙️ Recording in progress...")

    # Render visit records
    render_visit_records(db_manager)
else:
    st.info("Please select a patient from the sidebar")
