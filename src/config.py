import os
from dotenv import load_dotenv
load_dotenv()


CODMON_EMAIL = os.getenv('CODMON_EMAIL')
CODMON_PASSWORD = os.getenv('CODMON_PASSWORD')
CODMON_DOWNLOAD_PATH = os.getenv('CODMON_DOWNLOAD_PATH')
DRIVE_FOLDER_NAME = os.getenv('DRIVE_FOLDER_NAME')
