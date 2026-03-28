FROM python:3.11-slim

WORKDIR /app
# Install OS packages required to build cryptography if needed
RUN apt-get update \
	&& apt-get install -y --no-install-recommends \
	   build-essential \
	   libssl-dev \
	   libffi-dev \
	   python3-dev \
	   cargo \
	&& rm -rf /var/lib/apt/lists/*

# Upgrade packaging tools to prefer prebuilt wheels
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

EXPOSE 5000

CMD ["gunicorn", "--config", "gunicorn.conf.py", "wsgi:app"]
