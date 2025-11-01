# (PENAMBAHAN KODE) Dockerfile khusus untuk service gateway
# Menggunakan base image python slim dan menambahkan dependensi yang diperlukan.
# FASE 3 - ROADMAP OPEN CORE MVP (SIMPLIFIED DEPENDENCIES)

# Gunakan base image Python yang ringan
FROM python:3.11-slim

# Set working directory di dalam container
WORKDIR /app

# (MODIFIED FASE 3) Install curl DAN sqlite3
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    sqlite3 \
    libsqlite3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Salin file requirements dan install library Python
COPY requirements.txt .
# (MODIFIED FASE 3) Mungkin perlu build wheel untuk cryptography? Coba tanpa dulu.
RUN pip install --no-cache-dir -r requirements.txt

# Salin sisa dari source code aplikasi
COPY . .

# (MODIFIED FASE 3) Buat direktori data untuk SQLite DB
RUN mkdir -p /app/data

# Expose port (meskipun mapping dilakukan di docker-compose)
EXPOSE 8000

# Command dijalankan via entrypoint di docker-compose
# ENTRYPOINT ["/bin/sh", "-c", "chmod +x ./entrypoint.sh && ./entrypoint.sh"]