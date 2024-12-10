from streamlit_mic_recorder import mic_recorder
import streamlit as st
import io
from openai import OpenAI
from deepgram import DeepgramClient, PrerecordedOptions
import os
import asyncio


def whisper_stt(openai_api_key=None, start_prompt="🔴 Start Recording", stop_prompt="⏹️ Stop Recording", just_once=False,
                use_container_width=False, language=None, callback=None, args=(), kwargs=None, key=None):
    if not 'openai_client' in st.session_state:
        st.session_state.openai_client = OpenAI(
            api_key=openai_api_key or os.getenv('OPENAI_API_KEY'))
    if not '_last_speech_to_text_transcript_id' in st.session_state:
        st.session_state._last_speech_to_text_transcript_id = 0
    if not '_last_speech_to_text_transcript' in st.session_state:
        st.session_state._last_speech_to_text_transcript = None
    if key and not key + '_output' in st.session_state:
        st.session_state[key + '_output'] = None
    audio = mic_recorder(start_prompt=start_prompt, stop_prompt=stop_prompt, just_once=just_once,
                         use_container_width=use_container_width, format="wav", key=key)
    new_output = False
    if audio is None:
        output = None
    else:
        id = audio['id']
        new_output = (id > st.session_state._last_speech_to_text_transcript_id)
        if new_output:
            output = None
            st.session_state._last_speech_to_text_transcript_id = id
            audio_bio = io.BytesIO(audio['bytes'])
            audio_bio.name = 'audio.wav'
            success = False
            err = 0
            # Retry up to 3 times in case of OpenAI server error.
            while not success and err < 3:
                try:
                    transcript = st.session_state.openai_client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_bio,
                        language=language
                    )
                except Exception as e:
                    print(str(e))  # log the exception in the terminal
                    err += 1
                else:
                    success = True
                    output = transcript.text
                    st.session_state._last_speech_to_text_transcript = output
        elif not just_once:
            output = st.session_state._last_speech_to_text_transcript
        else:
            output = None

    if key:
        st.session_state[key + '_output'] = output
    if new_output and callback:
        callback(*args, **(kwargs or {}))
    return output


async def transcribe_audio(audio_bytes, deepgram_client, language=None):
    try:
        options = PrerecordedOptions(
            smart_format=True,
            punctuate=True,
            language=language or "en",
            model="nova-2"
        )

        # Create a dict with buffer and mimetype
        payload = {
            "buffer": audio_bytes,
            "mimetype": "audio/wav"
        }

        # Use transcribe_file for audio data from buffer
        response = await deepgram_client.listen.asyncrest.v("1").transcribe_file(
            payload,
            options
        )

        # Extract transcript from the response structure
        return response["results"]["channels"][0]["alternatives"][0]["transcript"]
    except Exception as e:
        st.error(f"Transcription error: {str(e)}")
        return None


def deepgram_stt(deepgram_api_key=None, start_prompt="🔴 Start Recording", stop_prompt="⏹️ Stop Recording",
                 just_once=False, use_container_width=False, language=None, callback=None, args=(),
                 kwargs=None, key=None):
    if not 'deepgram_client' in st.session_state:
        st.session_state.deepgram_client = DeepgramClient(
            api_key=deepgram_api_key or os.getenv('DEEPGRAM_API_KEY'))
    if not '_last_speech_to_text_transcript_id' in st.session_state:
        st.session_state._last_speech_to_text_transcript_id = 0
    if not '_last_speech_to_text_transcript' in st.session_state:
        st.session_state._last_speech_to_text_transcript = None
    if key and not key + '_output' in st.session_state:
        st.session_state[key + '_output'] = None

    audio = mic_recorder(start_prompt=start_prompt, stop_prompt=stop_prompt, just_once=just_once,
                         use_container_width=use_container_width, format="wav", key=key)

    new_output = False
    if audio is None:
        output = None
    else:
        id = audio['id']
        new_output = (id > st.session_state._last_speech_to_text_transcript_id)
        if new_output:
            output = None
            st.session_state._last_speech_to_text_transcript_id = id

            # Show processing message
            with st.spinner('Transcribing audio...'):
                # Run async transcription in sync context
                output = asyncio.run(transcribe_audio(
                    audio['bytes'],
                    st.session_state.deepgram_client,
                    language
                ))

            st.session_state._last_speech_to_text_transcript = output

        elif not just_once:
            output = st.session_state._last_speech_to_text_transcript
        else:
            output = None

    if key:
        st.session_state[key + '_output'] = output
    if new_output and callback:
        callback(*args, **(kwargs or {}))
    return output
