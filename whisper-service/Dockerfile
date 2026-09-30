FROM python:3.11-slim
COPY requirements.txt .
RUN python -m pip install --no-cache-dir --upgrade pip==26.2.1 \
    && python -m pip install --no-cache-dir --break-system-packages -r requirements.txt
RUN useradd --create-home whisperuser
WORKDIR /app
COPY --chown=whisperuser:whisperuser main.py .
ENV HF_HOME=/home/whisperuser/.cache/huggingface
RUN mkdir -p /home/whisperuser/.cache/huggingface \
    && chown -R whisperuser:whisperuser /home/whisperuser/.cache
USER whisperuser
EXPOSE 8001
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
