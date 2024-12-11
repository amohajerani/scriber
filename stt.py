from audio_recorder_streamlit import audio_recorder
import streamlit as st
import io
from openai import OpenAI

from deepgram import DeepgramClient, PrerecordedOptions
import os
import httpx
import asyncio


async def transcribe_audio(audio_bytes, deepgram_client, language=None):

    try:
        # Initialize the Deepgram client
        deepgram = DeepgramClient()

        # Set up transcription options
        options = PrerecordedOptions(
            model="nova-2",  # Using their latest model
            smart_format=True,  # Enable smart formatting
            language="en",  # Set to English
            punctuate=True,  # Add punctuation
        )

        # Create the source dictionary with the audio buffer
        source = {'buffer': audio_data}

        # Request transcription with increased timeout for larger files
        response = deepgram.listen.rest.v("1").transcribe_file(
            source,
            options,
            timeout=httpx.Timeout(300.0, connect=10.0)
        )

        # Extract transcript from the response structure
        return response["results"]["channels"][0]["alternatives"][0]["transcript"]
    except Exception as e:
        st.error(f"Transcription error: {str(e)}")
        return None


def deepgram_stt(deepgram_api_key=None):
    if not 'deepgram_client' in st.session_state:
        st.session_state.deepgram_client = DeepgramClient(
            api_key=deepgram_api_key or os.getenv('DEEPGRAM_API_KEY'))

    output = None
    audio = audio_recorder(
        text="",
        recording_color="#e8576e",
        neutral_color="#6aa36f",
        icon_size="2x",
    )

    if audio:
        with st.spinner('Transcribing audio...'):
            # Run async transcription in sync context
            output = asyncio.run(transcribe_audio(
                audio,
                st.session_state.deepgram_client,
            ))

    return output
