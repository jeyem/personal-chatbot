FROM python:3.12-slim
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# build numpy from source for this CPU before anything else
RUN pip install --no-cache-dir "numpy==1.26.4" --no-binary numpy

COPY requirements.txt .

# install rest of requirements — numpy already installed won't be reinstalled
RUN pip install --no-cache-dir -r requirements.txt --no-deps numpy

RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

COPY . .
EXPOSE 8000
CMD ["python", "serve.py"]