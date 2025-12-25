
import os

# Database Configuration (Giữ nguyên config của bạn)
DB_HOST = '127.0.0.1'
DB_USER = 'root'
DB_PASSWORD = 'hoangdh123'
DB_NAME = 'traffic_violations_db'

# Flask Configuration
SECRET_KEY = 'dev-key-traffic-violations'
DEBUG = True

# Upload Configuration
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv'}

# Model paths
HAARCASCADE_PATH = 'haarcascade_russian_plate_number.xml'