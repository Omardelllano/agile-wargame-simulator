FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml .
COPY wargame/ ./wargame/
RUN pip install -e .
EXPOSE 8000
CMD ["python", "-m", "wargame", "serve", "--port", "8000"]
