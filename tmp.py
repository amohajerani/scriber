import streamlit as st
from audio_recorder_streamlit import audio_recorder
import time
from datetime import datetime

st.title("Audio Recorder App")

# Add a brief description
st.write("Click the microphone button below to start recording audio")

# Create a placeholder for the audio recorder
audio_bytes = audio_recorder(
    text="",
    recording_color="#e8576e",
    neutral_color="#6aa36f",
    icon_size="2x",
)

# If audio is recorded, display it
if audio_bytes:
    # Generate a timestamp for the filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"recording_{timestamp}.wav"

    # Save the recorded audio
    with open(filename, "wb") as f:
        f.write(audio_bytes)

    # Display success message
    st.success(f"Audio saved as {filename}")
