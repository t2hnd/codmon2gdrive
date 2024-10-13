from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time
import config
import json
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow


# Set up logging to both console and file
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler("codmon_2_gdrive.log"),
                        logging.StreamHandler()
                    ])
logger = logging.getLogger(__name__)


class Codmon2Gdrive:
    def __init__(self):
        logger.info("Initializing Codmon2Gdrive")
        self.create_download_directory()
        self.driver = self.setup_driver()
        self.wait = WebDriverWait(self.driver, 10)
        self.drive_service = self.setup_drive_service()
        self.folder_id = self.get_or_create_folder(
            os.environ['DRIVE_FOLDER_NAME'])
        logger.info(f"Using folder ID: {self.folder_id}")
        self.clear_download_folder()

    def setup_driver(self):
        logger.info("Setting up Selenium WebDriver")
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_experimental_option("prefs", {
            "download.default_directory": os.environ.get('CODMON_DOWNLOAD_PATH', '/tmp/codmon_downloads'),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True
        })
        return webdriver.Chrome(options=chrome_options)

    def setup_drive_service(self):
        logger.info("Setting up Drive service")
        SCOPES = ['https://www.googleapis.com/auth/drive.file']

        service_account_info = json.loads(
            os.environ['GOOGLE_SERVICE_ACCOUNT_KEY'])
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info, scopes=SCOPES)

        logger.info("Drive service set up successfully")
        return build('drive', 'v3', credentials=credentials)

    def get_or_create_folder(self, folder_name):
        logger.info(f"Getting or creating folder: {folder_name}")
        query = f"name='{
            folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = self.drive_service.files().list(
            q=query, spaces='drive', fields='files(id, name)').execute()
        folders = results.get('files', [])

        if not folders:
            logger.info(f"Folder '{folder_name}' not found. Creating it.")
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = self.drive_service.files().create(
                body=folder_metadata, fields='id').execute()
            return folder.get('id')
        else:
            logger.info(f"Folder '{folder_name}' found with ID: {
                        folders[0]['id']}")
            return folders[0]['id']

    def create_download_directory(self):
        download_path = os.environ.get(
            'CODMON_DOWNLOAD_PATH', '/tmp/codmon_downloads')
        os.makedirs(download_path, exist_ok=True)
        logger.info(f"Download directory created/verified: {download_path}")

    def clear_download_folder(self):
        download_path = os.environ.get(
            'CODMON_DOWNLOAD_PATH', '/tmp/codmon_downloads')
        for filename in os.listdir(download_path):
            file_path = os.path.join(download_path, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                logger.error(f'Failed to delete {file_path}. Reason: {e}')
        logger.info(f"Download folder cleared: {download_path}")

    def login(self):
        logger.info("Logging in to Codmon")
        self.driver.get("https://parents.codmon.com/menu")
        time.sleep(4)

        self.click_element(
            "body > div > div:nth-child(1) > ons-page > ons-page > div.page__content > ons-navigator > ons-page > div.page__content > section > div.menu__loginLink")
        time.sleep(4)

        self.input_text(
            "body > div > div:nth-child(1) > ons-page > ons-page > div.page__content > ons-navigator > ons-page > div.page__content > div.loginPage--parent > section > input", os.environ['CODMON_EMAIL'])
        self.input_text(
            "body > div > div:nth-child(1) > ons-page > ons-page > div.page__content > ons-navigator > ons-page > div.page__content > div.loginPage--parent > section > div:nth-child(4) > input", os.environ['CODMON_PASSWORD'])
        self.click_element(
            "body > div > div:nth-child(1) > ons-page > ons-page > div.page__content > ons-navigator > ons-page > div.page__content > div.loginPage--parent > section > ons-button")
        time.sleep(4)
        logger.info("Login successful")

    def navigate_to_resource_room(self):
        logger.info("Navigating to resource room")
        self.click_element(
            "body > div > div:nth-child(1) > ons-page > div:nth-child(3) > ons-tabbar > div.tabbar.ons-tabbar__footer.ons-swiper-tabbar > ons-tab.serviceInActiveIcon.tabIcon.tabbar__item > button")
        time.sleep(4)
        self.click_element(
            "#service_page > div.page__content > ons-navigator > ons-page > div.page__content > div > div > section > ul > li:nth-child(1)")
        time.sleep(3)
        logger.info("Navigated to resource room")

    def process_posts(self):
        logger.info("Processing posts")
        while True:
            posts = self.driver.find_elements(
                By.CSS_SELECTOR, "#service_page > div.page__content > ons-navigator > ons-page:nth-child(2) > div.page__content > div > div:nth-child(3) > ul > li > div")

            for post in posts[:min(20, len(posts))]:
                self.process_single_post(post)

            if not self.go_to_next_page():
                break
        logger.info("Finished processing posts")

    def process_single_post(self, post):
        logger.info("Processing a single post")
        post.click()
        time.sleep(2)

        prefix_selector = "#service_page > div.page__content > ons-navigator > ons-page.handoutDetailPage.selectable-container.page > div.page__content > div > div.handoutDetailContainer > div.handoutDetailFooter > div.handoutPublishedPeriod"
        prefix_element = self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, prefix_selector)))
        prefix = prefix_element.text.strip().replace(" ", "_")

        files = self.driver.find_elements(
            By.CSS_SELECTOR, "#service_page > div.page__content > ons-navigator > ons-page.handoutDetailPage.selectable-container.page > div.page__content > div > div.attachmentContainer > div:nth-child(2) > ul > li > span.attachment_link")

        original_window = self.driver.current_window_handle

        for file in files:
            file_path = self.download_file(file, original_window)
            if file_path:
                logger.info(f"File downloaded: {file_path}")
                self.upload_to_drive(file_path, prefix)
            else:
                logger.warning(f"File download failed for: {file.text}")

        self.click_element(
            "#service_page > div.page__content > ons-navigator > ons-page.handoutDetailPage.selectable-container.page > ons-toolbar > div.left.toolbar__left > ons-back-button > span.back-button__label")
        time.sleep(1)

    def download_file(self, file, original_window):
        logger.info(f"Downloading: {file.text}")
        assert len(self.driver.window_handles) == 1

        file.click()
        self.wait.until(EC.number_of_windows_to_be(2))

        for window_handle in self.driver.window_handles:
            if window_handle != original_window:
                self.driver.switch_to.window(window_handle)
                break

        time.sleep(2)
        self.driver.close()
        self.driver.switch_to.window(original_window)

        file_name = file.text
        file_path = os.path.join(os.environ.get(
            'CODMON_DOWNLOAD_PATH', '/tmp/codmon_downloads'), file_name)
        timeout = time.time() + 60  # 1 minute timeout
        while not os.path.exists(file_path):
            if time.time() > timeout:
                logger.error(f"Timeout: File {file_name} was not downloaded")
                return None
            time.sleep(1)

        return file_path

    def file_exists_in_folder(self, file_name):
        query = f"name='{file_name}' and '{
            self.folder_id}' in parents and trashed=false"
        results = self.drive_service.files().list(
            q=query, spaces='drive', fields='files(id, name)').execute()
        return len(results.get('files', [])) > 0

    def upload_to_drive(self, file_path, prefix):
        logger.info(f"Attempting to upload file: {file_path}")
        original_file_name = os.path.basename(file_path)
        new_file_name = f"{prefix}_{original_file_name}"

        if self.file_exists_in_folder(new_file_name):
            logger.info(
                f"File '{new_file_name}' already exists in the folder. Skipping upload.")
            return

        file_metadata = {
            'name': new_file_name,
            'parents': [self.folder_id]
        }
        media = MediaFileUpload(file_path, resumable=True)

        try:
            file = self.drive_service.files().create(
                body=file_metadata, media_body=media, fields='id').execute()
            logger.info(f'File ID: {file.get("id")} uploaded to folder: {
                        os.environ["DRIVE_FOLDER_NAME"]}')
        except Exception as e:
            logger.error(f"Error uploading file: {e}")

    def go_to_next_page(self):
        next_button = self.driver.find_element(
            By.CSS_SELECTOR, "#service_page > div.page__content > ons-navigator > ons-page:nth-child(2) > div.page__content > div > div:nth-child(3) > div.basicPagination > ul > li:nth-child(2) > div > button")
        if next_button.get_attribute("disabled") is None:
            next_button.click()
            time.sleep(3)
            logger.info("Navigated to next page")
            return True
        logger.info("No more pages to process")
        return False

    def click_element(self, selector):
        element = self.driver.find_element(By.CSS_SELECTOR, selector)
        element.click()

    def input_text(self, selector, text):
        element = self.driver.find_element(By.CSS_SELECTOR, selector)
        element.send_keys(text)

    def run(self):
        logger.info("Starting Codmon to Google Drive process")
        try:
            self.login()
            self.navigate_to_resource_room()
            self.process_posts()
        except Exception as e:
            logger.error(f"Error during scraping: {e}", exc_info=True)
        finally:
            self.driver.quit()
            logger.info("Codmon to Google Drive process completed")


if __name__ == "__main__":
    scraper = Codmon2Gdrive()
    scraper.run()
