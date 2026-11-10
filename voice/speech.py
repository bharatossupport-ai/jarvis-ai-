"""Push-to-talk recording, local transcription (Faster-Whisper) and speech (Piper).
No wake-word: the mic is only open while the user holds the talk button."""
import io
import tempfile
import threading
import wave
import numpy as np

SAMPLE_RATE = 16000


class Recorder:
    def __init__(self, device=None):
        self.device, self.frames, self.stream = device, [], None
        self.recording = False

    def start(self):
        import sounddevice as sd
        self.frames, self.recording = [], True
        self.stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16",
                                     device=self.device, callback=lambda d, *_: self.frames.append(d.copy()))
        self.stream.start()

    def stop(self):
        self.recording = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        return np.concatenate(self.frames).flatten() if self.frames else np.zeros(0, dtype="int16")


class Transcriber:
    _model, _lock = None, threading.Lock()

    def __init__(self, size="base", language="auto"):
        self.size = size
        self.language = None if language in (None, "auto") else language  # "hi" forces Hindi

    def _load(self):
        with self._lock:
            if Transcriber._model is None:  # lazy load: keeps RAM free until first use
                from faster_whisper import WhisperModel
                Transcriber._model = WhisperModel(self.size, device="cpu", compute_type="int8")
        return Transcriber._model

    def transcribe(self, audio_int16):
        if audio_int16.size < SAMPLE_RATE // 4:
            return ""
        audio = audio_int16.astype("float32") / 32768.0
        segments, _ = self._load().transcribe(audio, language=self.language, vad_filter=True)
        return " ".join(s.text.strip() for s in segments).strip()


class Speaker:
    """Piper TTS. Returns a WAV path; the UI plays it and animates the 3D companion."""

    def __init__(self, voice_path):
        self.voice_path, self._voice = voice_path, None

    def available(self):
        return bool(self.voice_path)

    def synth(self, text) -> str:
        from piper import PiperVoice
        if self._voice is None:
            self._voice = PiperVoice.load(self.voice_path)
        out = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
        with wave.open(out, "wb") as wf:
            self._voice.synthesize_wav(text, wf) if hasattr(self._voice, "synthesize_wav") else self._voice.synthesize(text, wf)
        return out


def list_input_devices():
    try:
        import sounddevice as sd
        return [(i, d["name"]) for i, d in enumerate(sd.query_devices()) if d["max_input_channels"] > 0]
    except Exception:
        return []
