"""Eigenstaendiger Whisper-Transkriptionsdienst.
Laeuft als separater Container wegen GPU-Isolation (siehe Anforderungsdokument
Kapitel 10) und wird vom Backend ausschliesslich ueber HTTP angesprochen -
Audiodaten verlassen dabei nie das lokale Docker-Netzwerk (Privacy by Design,
F-26/F-28)."""

import tempfile
import os

from fastapi import FastAPI, UploadFile
from faster_whisper import WhisperModel

app = FastAPI(title="Vital Mapper - Whisper Service")

MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "small")
DEVICE = os.getenv("WHISPER_DEVICE", "cpu").lower()
COMPUTE_TYPE = os.getenv(
    "WHISPER_COMPUTE_TYPE", "float16" if DEVICE == "cuda" else "int8"
)
_model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)

# Domaenenspezifisches Vokabular als Prompt-Priming (F-36: Pflegefachbegriffe
# werden ohne Priming von generischen Whisper-Modellen haeufiger falsch erkannt)
NURSING_VOCABULARY_PROMPT = (
    "Blutdruck, Puls, Temperatur, Sauerstoffsaettigung, Rollator, Mobilisation, "
    "Schmerzskala, NRS, Dekubitus, Sturzereignis, Ausscheidung"
)


@app.post("/transcribe")
async def transcribe(audio: UploadFile, language: str = "de") -> dict:
    with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
        tmp.write(await audio.read())
        tmp.flush()
        segments, info = _model.transcribe(
            tmp.name, language=language, initial_prompt=NURSING_VOCABULARY_PROMPT
        )
        text = " ".join(segment.text.strip() for segment in segments)

    return {
        "text": text,
        "confidence": float(info.language_probability),
        "model_version": f"faster-whisper:{MODEL_SIZE}:{DEVICE}:{COMPUTE_TYPE}",
    }


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
