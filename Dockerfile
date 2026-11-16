FROM python:3.15.2-slim
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["sh", "-c", "([ -f data/index/vectors.npy ] || python -m app.rag) && uvicorn app.main:app --host 0.0.0.0 --port 8000"]