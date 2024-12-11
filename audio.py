import pyaudio
import numpy as np
import wave
import io
import queue
import threading


class AudioRecorder:
    def __init__(self):
        self.sample_rate = 44100
        self.channels = 1
        self.chunk_size = 1024  # Number of frames per buffer
        self.audio_format = pyaudio.paInt16
        self.audio_queue = queue.Queue()
        self.recording_data = []
        self.is_recording = False
        self.stream = None
        self.audio = pyaudio.PyAudio()

    def audio_callback(self, in_data, frame_count, time_info, status):
        if status:
            print(f"Status: {status}")
        audio_data = np.frombuffer(in_data, dtype=np.int16)
        self.audio_queue.put(audio_data.copy())
        return (in_data, pyaudio.paContinue)

    def start_recording(self):
        self.recording_data = []
        self.is_recording = True
        self.stream = self.audio.open(
            format=self.audio_format,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size,
            stream_callback=self.audio_callback
        )
        self.stream.start_stream()

    def stop_recording(self):
        self.is_recording = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()

        # Process any remaining data in the queue
        while not self.audio_queue.empty():
            self.recording_data.append(self.audio_queue.get())

        if not self.recording_data:
            return None

        # Combine all audio chunks
        audio_data = np.concatenate(self.recording_data)

        # Convert to bytes
        byte_io = io.BytesIO()
        with wave.open(byte_io, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.audio.get_sample_size(self.audio_format))
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_data.tobytes())

        return byte_io.getvalue()

    def __del__(self):
        self.audio.terminate()
