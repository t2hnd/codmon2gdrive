# Codmon2GDrive

This tool downloads files from [codmon](https://www.codmon.com/) and upload them to Google Drive

# Setup

## Setup virtual environment

```sh
# Create virtual environment
python -m venv .venv

# activate
source .venv/bin/activate

# install modules
pip install -r requirements.txt
```

## Environmental variables

For this tool to automatically login into [codmon page](https://parents.codmon.com/menu) and do the scraping tasks.
Additionally, it requires upload path in Google Drive.
For this purpose, you should create `.env` and provide your own credentials.

```.env
CODMON_EMAIL=<email_to_login_codmon>
CODMON_PASSWORD=<password_to_login_codmon>
CODMON_DOWNLOAD_PATH=<path_to_save_downloaded_files>
DRIVE_FOLDER_ID=<google_drive_folder_id_to_upload_files>
```

You also need Google Drive credential setup.

## Run

```sh
python src/codmon_2_gdrive.py
```
