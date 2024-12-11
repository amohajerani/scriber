from deepgram import DeepgramClient, PrerecordedOptions
import os
import httpx


def deepgram_stt(audio_data):
    """
    Transcribe audio using Deepgram's API

    Args:
        audio_data (bytes): Raw audio data in bytes

    Returns:
        str: Transcribed text
    """
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

        # Extract the transcript from the response
        if response and response.results and response.results.channels:
            transcript = response.results.channels[0].alternatives[0].transcript
            return transcript

        return None

    except Exception as e:
        print(f"Error in transcription: {str(e)}")
        return None
