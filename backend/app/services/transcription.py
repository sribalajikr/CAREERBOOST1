"""Server-side speech-to-text fallback (free, offline).

The browser's SpeechRecognition API types the answer live while the student
speaks, but it is Chrome/Edge-only and can silently fail (e.g. embedded
browsers without Google's speech backend). When no live transcript was
captured, the frontend uploads the recorded audio here and Vosk — a fully
offline, open-source recognizer — transcribes it locally. No API key, no
cloud, nothing paid.

Pipeline: webm/opus (browser recording) → ffmpeg → 16 kHz mono WAV → Vosk.
The model lives in backend/models/vosk-model-small-en-us-0.15 (auto-download
instructions in backend/README.md). If the model or vosk package is missing,
the endpoint degrades gracefully and the UI keeps the typed-answer path.
"""
import json
import logging
import os
import subprocess
import tempfile
import wave

from app.core.config import settings

logger = logging.getLogger("uvicorn.app")

_model = None
_model_loaded = False


def _get_model():
    """Load the Vosk model once; returns None when unavailable."""
    global _model, _model_loaded
    if _model_loaded:
        return _model
    _model_loaded = True
    path = settings.VOSK_MODEL_PATH
    if not path or not os.path.isdir(path):
        logger.warning("Vosk model not found at %r — server transcription disabled.", path)
        return None
    try:
        from vosk import Model, SetLogLevel

        SetLogLevel(-1)
        _model = Model(path)
        logger.info("Vosk speech model loaded from %s", path)
    except Exception as exc:  # noqa: BLE001 - optional dependency
        logger.warning("Could not load Vosk (%s) — server transcription disabled.", exc)
        _model = None
    return _model


def transcription_available() -> bool:
    return _get_model() is not None


def _ffmpeg_exe() -> str | None:
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # noqa: BLE001 - optional dependency
        return None


def _to_wav_16k_mono(data: bytes) -> str | None:
    """Transcode any browser audio blob to 16 kHz mono PCM WAV via ffmpeg."""
    ff = _ffmpeg_exe()
    if not ff:
        return None
    tmp_in = None
    tmp_out = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
            f.write(data)
            tmp_in = f.name
        fd, tmp_out = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        proc = subprocess.run(
            [ff, "-y", "-hide_banner", "-loglevel", "error",
             "-i", tmp_in, "-ac", "1", "-ar", "16000", "-f", "wav", tmp_out],
            capture_output=True, timeout=120,
        )
        if proc.returncode != 0 or not os.path.exists(tmp_out):
            logger.warning("ffmpeg transcode failed: %s", proc.stderr[-200:] if proc.stderr else "?")
            return None
        return tmp_out
    except Exception as exc:  # noqa: BLE001
        logger.warning("ffmpeg transcode error: %s", exc)
        if tmp_out and os.path.exists(tmp_out):
            os.remove(tmp_out)
        return None
    finally:
        if tmp_in and os.path.exists(tmp_in):
            os.remove(tmp_in)


def transcribe_audio(data: bytes) -> dict:
    """Transcribe recorded audio bytes. Returns {text, engine, duration_seconds}.

    Raises RuntimeError when transcription is unavailable so the route can
    return a clean 503 and the UI can fall back to typing.
    """
    model = _get_model()
    if model is None:
        raise RuntimeError("Speech-to-text model is not installed on the server.")

    wav_path = _to_wav_16k_mono(data)
    if not wav_path:
        raise RuntimeError("Could not decode the recorded audio.")

    try:
        from vosk import KaldiRecognizer

        with wave.open(wav_path, "rb") as w:
            rate = w.getframerate()
            frames = w.getnframes()
            duration = round(frames / rate, 1) if rate else 0.0
            rec = KaldiRecognizer(model, rate)
            rec.SetWords(False)
            parts: list[str] = []
            while True:
                chunk = w.readframes(8000)  # 0.5 s of audio per read
                if not chunk:
                    break
                if rec.AcceptWaveform(chunk):
                    res = json.loads(rec.Result() or "{}")
                    if res.get("text"):
                        parts.append(res["text"])
            final = json.loads(rec.FinalResult() or "{}")
            if final.get("text"):
                parts.append(final["text"])
        text = " ".join(parts).strip()
        logger.info("Transcribed %.1fs of audio with Vosk (%d chars).", duration, len(text))
        return {"text": text, "engine": "vosk", "duration_seconds": duration}
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Transcription failed: {exc}") from exc
    finally:
        try:
            os.remove(wav_path)
        except OSError:
            pass
