#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\Dockerfile
# TOTAL LINES: 44
# NOTE: (ATTEMPT 11) PyPI name is 'hrw', not 'rendezvous...'. FINAL.
#######################################################################

# (Roadmap 1.F) Use slim image, pin version
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# --- (PENAMBAHAN KODE) ---
# Install 'dos2unix' utility to fix Windows CRLF line ending issues.
# Clean up apt cache afterward.
RUN apt-get update && \
    apt-get install -y dos2unix && \
    rm -rf /var/lib/apt/lists/*
# --- (AKHIR PENAMBAHAN KODE) ---

# Install dependencies
# (Roadmap 1.F) Use --no-cache-dir
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# (Roadmap 2.1, 2.3, 2.4, 3.1) Install extra libs
# ... (all other libs) ...
# hrw (Hashing/Cluster) <--- (INI DIA FIX-NYA YANG SEBENERNYA)
RUN pip install --no-cache-dir \
    msgpack \
    PyJWT \
    flask-jwt-extended \
    Flask-Cors \
    Flask-Migrate \
    Flask-Script \
    alembic \
    cryptography \
    prometheus-flask-exporter \
    requests \
    urllib3 \
    mmh3 \
    hrw \
    gunicorn

# Copy the rest of the app files
COPY . .

# (Roadmap 1.A) Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# --- (PENAMBAHAN KODE / MODIFIKASI) ---
# (FIX for Windows CRLF line endings)
# Use the dos2unix utility we just installed.
# RUN ["sed", "-i", "s/\\r$//", "/app/entrypoint.sh"] # (DI-KOMEN - Faulty sed command)
RUN dos2unix /app/entrypoint.sh
# --- (AKHIR PENAMBAHAN KODE) ---

# (Roadmap 1.A / 1.C)
ENTRYPOINT ["/app/entrypoint.sh"]

# Expose the port
EXPOSE 8000