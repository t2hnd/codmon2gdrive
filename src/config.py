import os
from dotenv import load_dotenv
load_dotenv()


CODMON_EMAIL = os.getenv('CODMON_EMAIL')
CODMON_PASSWORD = os.getenv('CODMON_PASSWORD')
# Use a temporary directory in GitHub Actions
CODMON_DOWNLOAD_PATH = '/tmp/codmon_downloads'
DRIVE_FOLDER_NAME = os.getenv('DRIVE_FOLDER_NAME')
