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
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow


class Codmon2Gdrive:
    def __init__(self):
        self.create_download_directory()
        self.driver = self.setup_driver()
        self.wait = WebDriverWait(self.driver, 10)
        self.drive_service = self.setup_drive_service()
        self.folder_id = self.get_or_create_folder(
            os.environ['DRIVE_FOLDER_NAME'])
        self.clear_download_folder()

    def create_download_directory(self):
        os.makedirs(config.CODMON_DOWNLOAD_PATH, exist_ok=True)
        print(
            f"Download directory created/verified: {config.CODMON_DOWNLOAD_PATH}")

    def setup_driver(self):
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_experimental_option("prefs", {
            "download.default_directory": config.CODMON_DOWNLOAD_PATH,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True
        })
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=chrome_options)

    def setup_drive_service(self):
        SCOPES = ['https://www.googleapis.com/auth/drive.file']

        service_account_info = json.loads(
            os.environ['GOOGLE_SERVICE_ACCOUNT_KEY'])
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info, scopes=SCOPES)

        return build('drive', 'v3', credentials=credentials)

    def get_or_create_folder(self, folder_name):
        # Check if folder already exists
        results = self.drive_service.files().list(
            q=f"mimeType='application/vnd.google-apps.folder' and name='{
                folder_name}' and trashed=false",
            spaces='drive',
            fields='files(id, name)').execute()
        folders = results.get('files', [])

        # If folder exists, return its ID
        if folders:
            return folders[0]['id']

        # If folder doesn't exist, create it
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        folder = self.drive_service.files().create(
            body=folder_metadata, fields='id').execute()
        return folder.get('id')

    def clear_download_folder(self):
        for filename in os.listdir(config.CODMON_DOWNLOAD_PATH):
            file_path = os.path.join(config.CODMON_DOWNLOAD_PATH, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f'Failed to delete {file_path}. Reason: {e}')
        print(f"Download folder cleared: {config.CODMON_DOWNLOAD_PATH}")

    def login(self):
        self.driver.get("https://parents.codmon.com/menu")
        time.sleep(2)

        self.click_element(
            "body > div > div:nth-child(1) > ons-page > ons-page > div.page__content > ons-navigator > ons-page > div.page__content > section > div.menu__loginLink")
        time.sleep(2)

        self.input_text("body > div > div:nth-child(1) > ons-page > ons-page > div.page__content > ons-navigator > ons-page > div.page__content > div.loginPage--parent > section > input", config.CODMON_EMAIL)
        self.input_text("body > div > div:nth-child(1) > ons-page > ons-page > div.page__content > ons-navigator > ons-page > div.page__content > div.loginPage--parent > section > div:nth-child(4) > input", config.CODMON_PASSWORD)
        self.click_element(
            "body > div > div:nth-child(1) > ons-page > ons-page > div.page__content > ons-navigator > ons-page > div.page__content > div.loginPage--parent > section > ons-button")
        time.sleep(2)

    def navigate_to_resource_room(self):
        self.click_element(
            "body > div > div:nth-child(1) > ons-page > div:nth-child(3) > ons-tabbar > div.tabbar.ons-tabbar__footer.ons-swiper-tabbar > ons-tab.serviceInActiveIcon.tabIcon.tabbar__item > button")
        time.sleep(2)
        self.click_element(
            "#service_page > div.page__content > ons-navigator > ons-page > div.page__content > div > div > section > ul > li:nth-child(1)")
        time.sleep(3)

    def process_posts(self):
        while True:
            posts = self.driver.find_elements(
                By.CSS_SELECTOR, "#service_page > div.page__content > ons-navigator > ons-page:nth-child(2) > div.page__content > div > div:nth-child(3) > ul > li > div")

            for post in posts[:min(20, len(posts))]:
                self.process_single_post(post)

            if not self.go_to_next_page():
                break

    def process_single_post(self, post):
        post.click()
        time.sleep(2)

        # Extract the prefix
        prefix_selector = "#service_page > div.page__content > ons-navigator > ons-page.handoutDetailPage.selectable-container.page > div.page__content > div > div.handoutDetailContainer > div.handoutDetailFooter > div.handoutPublishedPeriod"
        prefix_element = self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, prefix_selector)))
        prefix = prefix_element.text.strip().replace(
            " ", "_")  # Replace spaces with underscores

        files = self.driver.find_elements(
            By.CSS_SELECTOR, "#service_page > div.page__content > ons-navigator > ons-page.handoutDetailPage.selectable-container.page > div.page__content > div > div.attachmentContainer > div:nth-child(2) > ul > li > span.attachment_link")

        original_window = self.driver.current_window_handle

        for file in files:
            file_path = self.download_file(file, original_window)
            if file_path:
                self.upload_to_drive(file_path, prefix)

        self.click_element(
            "#service_page > div.page__content > ons-navigator > ons-page.handoutDetailPage.selectable-container.page > ons-toolbar > div.left.toolbar__left > ons-back-button > span.back-button__label")
        time.sleep(1)

    def download_file(self, file, original_window):
        print(f"Downloading: {file.text}")
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

        # Wait for the file to be downloaded
        file_name = file.text
        file_path = os.path.join(config.CODMON_DOWNLOAD_PATH, file_name)
        timeout = time.time() + 60  # 1 minute timeout
        while not os.path.exists(file_path):
            if time.time() > timeout:
                print(f"Timeout: File {file_name} was not downloaded")
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
        original_file_name = os.path.basename(file_path)
        new_file_name = f"{prefix}_{original_file_name}"

        if self.file_exists_in_folder(new_file_name):
            print(
                f"File '{new_file_name}' already exists in the folder. Skipping upload.")
            return

        file_metadata = {
            'name': new_file_name,
            'parents': [self.folder_id]
        }
        media = MediaFileUpload(file_path, resumable=True)
        file = self.drive_service.files().create(
            body=file_metadata, media_body=media, fields='id').execute()
        print(f'File ID: {file.get("id")} uploaded to folder: {
              config.DRIVE_FOLDER_NAME}')

    def go_to_next_page(self):
        next_button = self.driver.find_element(
            By.CSS_SELECTOR, "#service_page > div.page__content > ons-navigator > ons-page:nth-child(2) > div.page__content > div > div:nth-child(3) > div.basicPagination > ul > li:nth-child(2) > div > button")
        if next_button.get_attribute("disabled") is None:
            next_button.click()
            time.sleep(3)
            return True
        return False

    def click_element(self, selector):
        element = self.driver.find_element(By.CSS_SELECTOR, selector)
        element.click()

    def input_text(self, selector, text):
        element = self.driver.find_element(By.CSS_SELECTOR, selector)
        element.send_keys(text)

    def run(self):
        try:
            self.login()
            self.navigate_to_resource_room()
            self.process_posts()
        finally:
            self.driver.quit()


if __name__ == "__main__":
    scraper = Codmon2Gdrive()
    scraper.run()
