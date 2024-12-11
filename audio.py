import sounddevice as sd
import numpy as np
import wave
import io
import queue
import threading


class AudioRecorder:
    def __init__(self):
        self.sample_rate = 44100
        self.channels = 1
        self.audio_queue = queue.Queue()
        self.recording_data = []
        self.is_recording = False
        self.stream = None

    def audio_callback(self, indata, frames, time, status):
        if status:
            print(f"Status: {status}")
        self.audio_queue.put(indata.copy())

    def start_recording(self):
        self.recording_data = []
        self.is_recording = True
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=np.int16,
            callback=self.audio_callback
        )
        self.stream.start()

    def stop_recording(self):
        self.is_recording = False
        if self.stream:
            self.stream.stop()
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
            wf.setsampwidth(2)  # 2 bytes for int16
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_data.tobytes())

        return byte_io.getvalue()
