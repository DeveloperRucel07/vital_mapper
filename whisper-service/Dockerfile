FROM python:3.11-slim
RUN pip install --no-cache-dir --break-system-packages \
    fastapi uvicorn[standard] faster-whisper python-multipart
COPY main.py .
EXPOSE 8001
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
