import streamlit as st
import pyaudio
import wave
import numpy as np
from datetime import datetime


def record_audio(duration, sample_rate=44100, chunk=1024, channels=1):
    # Initialize PyAudio
    audio = pyaudio.PyAudio()

    # Open stream
    stream = audio.open(
        format=pyaudio.paFloat32,
        channels=channels,
        rate=sample_rate,
        input=True,
        frames_per_buffer=chunk
    )

    # Initialize list to store frames
    frames = []

    # Calculate total chunks to record
    total_chunks = int((sample_rate * duration) / chunk)

    # Create a placeholder for the progress
    progress_text = st.empty()

    try:
        # Record audio until stop is pressed or duration is reached
        for i in range(total_chunks):
            if not st.session_state.is_recording:
                break

            # Show progress
            progress_text.text(f"Recording: {i/total_chunks*100:.1f}%")

            data = stream.read(chunk)
            frames.append(data)

    finally:
        # Clean up
        stream.stop_stream()
        stream.close()
        audio.terminate()
        progress_text.empty()

    return b''.join(frames)


def save_audio(audio_data, filename, sample_rate=44100, channels=1):
    # Convert audio data to numpy array
    audio_array = np.frombuffer(audio_data, dtype=np.float32)

    # Convert to int16 format
    audio_int16 = (audio_array * 32767).astype(np.int16)

    # Create WAV file
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)  # 2 bytes for int16
        wf.setframerate(sample_rate)
        wf.writeframes(audio_int16.tobytes())


# Initialize session state
if 'is_recording' not in st.session_state:
    st.session_state.is_recording = False
if 'audio_data' not in st.session_state:
    st.session_state.audio_data = None
if 'recording_complete' not in st.session_state:
    st.session_state.recording_complete = False

# Streamlit UI
st.title("Audio Recorder")

# Recording duration input
duration = st.slider("Recording Duration (seconds)", 1, 10, 5)

col1, col2 = st.columns(2)

# Start recording button
with col1:
    if st.button("Start Recording"):
        st.session_state.is_recording = True
        st.session_state.recording_complete = False
        st.write("Recording... Press 'Stop Recording' to finish early.")

        # Record audio
        audio_data = record_audio(duration)

        if len(audio_data) > 0:  # Check if we have any audio data
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"recording_{timestamp}.wav"

            # Save audio file
            save_audio(audio_data, filename)
            st.session_state.recording_complete = True
            st.success(f"Recording saved as {filename}")

            # Add audio playback
            st.audio(filename)

        st.session_state.is_recording = False

# Stop recording button
with col2:
    if st.button("Stop Recording"):
        if st.session_state.is_recording:
            st.session_state.is_recording = False
            st.session_state.recording_complete = True

# Show status
if st.session_state.recording_complete:
    st.write("Recording completed and saved!")
