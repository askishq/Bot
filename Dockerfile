FROM python:3.10-slim

RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# -u যুক্ত করায় লগে ইনস্ট্যান্ট রেসপন্স দেখা যাবে
CMD ["python", "-u", "bot_termux.py"]
