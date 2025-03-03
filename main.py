# -*- coding: utf-8 -*-
import os
import time
import signal
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import ffmpeg
from dotenv import load_dotenv

load_dotenv()

class TikTokAutoUploader:
    def __init__(self):
        # Kill existing chrome processes
        self.cleanup_chrome_processes()
        
        self.fb_page_id = os.getenv('FB_PAGE_ID')
        self.fb_token = os.getenv('FB_PAGE_TOKEN')
        self.driver = self.init_whatsapp()
        self.wait = WebDriverWait(self.driver, 30)
        self.session_id = int(time.time())

    def cleanup_chrome_processes(self):
        os.system('pkill -f chrome')
        time.sleep(1)  # Beri waktu untuk terminate processes

    def init_whatsapp(self):
        chrome_options = Options()
        
        # Konfigurasi untuk server
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--remote-debugging-port=9222')
        
        # Buat session directory unik
        session_dir = f"./sessions/{self.session_id}"
        chrome_options.add_argument(f'--user-data-dir={session_dir}')
        
        # Auto-install ChromeDriver
        service = ChromeService(ChromeDriverManager().install())
        
        return webdriver.Chrome(
            service=service,
            options=chrome_options
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.driver.quit()
        self.cleanup_chrome_processes()

    def listen_messages(self):
        print('Menunggu QR Code...')
        self.wait.until(EC.presence_of_element_located(
            (By.XPATH, '//canvas[@aria-label="Scan me!"]')))
        
        print('Menunggu pesan...')
        while True:
            try:
                unread = self.wait.until(EC.presence_of_element_located(
                    (By.XPATH, '//div[contains(@class, "_1pJ9J")]')))
                if unread:
                    self.process_new_messages()
            except Exception as e:
                print(f'Error: {str(e)}')
            time.sleep(5)

    def process_new_messages(self):
        messages = self.driver.find_elements(
            By.XPATH, '//div[contains(@class, "message-in")]')
        
        for msg in messages[-5:]:
            try:
                text_element = msg.find_element(
                    By.CSS_SELECTOR, 'span._11JPr.selectable-text.copyable-text')
                text = text_element.text
                
                if text.startswith(('!s', '!l')):
                    self.handle_command(msg, text)
            except Exception as e:
                print(f'Error membaca pesan: {str(e)}')

    def handle_command(self, msg, text):
        try:
            if text.startswith('!s'):
                link = text.split(' ', 1)[1]
                self.process_single(link)
                self.reply(msg, '[SUKSES] Video diproses!')
                
            elif text.startswith('!l'):
                links = [ln.strip() for ln in text.split('\n')[1:] if ln.strip()]
                for idx, link in enumerate(links):
                    self.process_single(link)
                    if idx < len(links) - 1:
                        time.sleep(30)
                self.reply(msg, f'[SUKSES] {len(links)} video selesai!')
                
        except Exception as e:
            self.reply(msg, f'[GAGAL] {str(e)}')

    def reply(self, msg, text):
        try:
            msg.click()
            input_box = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, '//div[@title="Ketikan pesan"]')))
            input_box.send_keys(text + '\n')
        except Exception as e:
            print(f'Gagal membalas: {str(e)}')

    def download_tiktok(self, url):
        api_url = 'https://api.tikmate.app/api/lookup'
        try:
            response = requests.post(api_url, data={'url': url}, timeout=10)
            data = response.json()
            return {
                'video_url': data['video_url'],
                'description': data.get('description', ''),
                'author': data.get('author_name', 'Unknown')
            }
        except Exception as e:
            raise Exception(f'Gagal download TikTok: {str(e)}')

    def edit_metadata(self, input_path, metadata):
        output_path = f"output_{self.session_id}.mp4"
        
        try:
            stream = ffmpeg.input(input_path)
            stream = ffmpeg.output(
                stream,
                output_path,
                **{
                    'metadata': f'title="{metadata["description"]}"',
                    'metadata:s:v': 'title="TikTok Video"',
                    'metadata:s:a': 'title="TikTok Audio"',
                    'c': 'copy'
                }
            )
            ffmpeg.run(stream, overwrite_output=True, quiet=True)
            return output_path
        except Exception as e:
            raise Exception(f'Gagal edit metadata: {str(e)}')

    def upload_to_facebook(self, video_path, metadata):
        try:
            caption = f"{metadata['description']}\n\nCredit: @{metadata['author']} #TikTok #Viral"
            
            with open(video_path, 'rb') as f:
                response = requests.post(
                    f'https://graph.facebook.com/{self.fb_page_id}/video_reels',
                    files={'video_file': f},
                    data={
                        'access_token': self.fb_token,
                        'caption': caption,
                        'published': 'true'
                    },
                    timeout=30
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            raise Exception(f'Gagal upload ke Facebook: {str(e)}')

    def process_single(self, url):
        temp_path = None
        edited_path = None
        
        try:
            # Step 1: Download TikTok
            data = self.download_tiktok(url)
            
            # Step 2: Simpan video sementara
            temp_path = f'temp_{self.session_id}.mp4'
            with requests.get(data['video_url'], stream=True, timeout=10) as r:
                r.raise_for_status()
                with open(temp_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            
            # Step 3: Edit metadata
            edited_path = self.edit_metadata(temp_path, data)
            
            # Step 4: Upload ke Facebook
            result = self.upload_to_facebook(edited_path, data)
            print('Upload berhasil:', result.get('id', 'Unknown'))
            
        except Exception as e:
            print(f'Error proses: {str(e)}')
            raise
        finally:
            # Step 5: Cleanup
            for path in [temp_path, edited_path]:
                if path and os.path.exists(path):
                    os.remove(path)

if __name__ == '__main__':
    with TikTokAutoUploader() as bot:
        bot.listen_messages()
