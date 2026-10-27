import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# ------------------------------------------------------------------------------
# MySQL connection
# ------------------------------------------------------------------------------
# The app and MySQL Workbench must use this same schema: airline_db.
# database/airline_db.sql creates the schema, demo data, triggers and the
# airline_app user. If you prefer different credentials, set the environment
# variables below before starting the app.
DB_HOST = os.environ.get('DB_HOST', '127.0.0.1').strip()
DB_PORT = int(os.environ.get('DB_PORT', '3306'))
DB_USER = os.environ.get('DB_USER', 'airline_app').strip()
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'airline123')
DB_NAME = os.environ.get('DB_NAME', 'airline_db').strip()

# ------------------------------------------------------------------------------
# Timezone
# ------------------------------------------------------------------------------
# The whole application stores and displays Indian Standard Time. MySQL is put
# in the +05:30 session timezone on every connection, so CURRENT_TIMESTAMP in
# table defaults and triggers also writes IST.
TIMEZONE_NAME = 'Asia/Kolkata'
TIMEZONE_LABEL = 'IST'
TIMEZONE_OFFSET = '+05:30'

# ------------------------------------------------------------------------------
# Flask
# ------------------------------------------------------------------------------
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'skyreserve-airline-reservation-dbms-project-2026'
)
DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 'yes')
PORT = int(os.environ.get('PORT', '5000'))

# Set this to False after the first run if you do not want browser auto-reload.
TEMPLATES_AUTO_RELOAD = DEBUG
