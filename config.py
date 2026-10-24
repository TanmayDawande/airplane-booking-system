import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Database configuration
ON_VERCEL = bool(os.environ.get('VERCEL'))

DB_ENGINE = os.environ.get('DB_ENGINE', 'sqlite' if ON_VERCEL else 'auto').lower() # 'auto', 'mysql', or 'sqlite'
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = int(os.environ.get('DB_PORT', 3306))
DB_USER = os.environ.get('DB_USER', 'root')
DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
DB_NAME = os.environ.get('DB_NAME', 'airline_db')
SQLITE_PATH = BASE_DIR / 'airline_db.sqlite3'

if ON_VERCEL:
    # Vercel's filesystem is read-only except /tmp, and SQLite needs to write.
    # Work on a copy. It resets whenever the serverless instance restarts.
    import shutil
    _tmp_db = Path('/tmp/airline_db.sqlite3')
    if not _tmp_db.exists():
        shutil.copyfile(SQLITE_PATH, _tmp_db)
    SQLITE_PATH = _tmp_db

SECRET_KEY = os.environ.get('SECRET_KEY', 'aeroreserve-quantum-super-secret-key-2026')
DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() in ('true', '1', 'yes')
PORT = int(os.environ.get('PORT', 5000))
