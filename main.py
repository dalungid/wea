# -*- coding: utf-8 -*-
import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import ffmpeg
from dotenv import load_dotenv

load_dotenv()

class TikTokAutoUploader:
    def __init__(self):
        self.fb_page_id = os.getenv('FB_PAGE_ID')
        self.fb_token = os.getenv('FB_PAGE_TOKEN')
        self.driver = self.init_whatsapp()
        self.wait = WebDriverWait(self.driver, 30)

    def init_whatsapp(self):
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('user-data-dir=./sessions')
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.get('https://web.whatsapp.com/')
        return driver

    def listen_messages(self):
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
            if not msg.get_attribute('data-id'):
                continue

            try:
                text_element = msg.find_element(By.CSS_SELECTOR, 'span._11JPr.selectable-text.copyable-text')
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
        response = requests.post(api_url, data={'url': url})
        data = response.json()
        
        return {
            'video_url': data['video_url'],
            'description': data['description'],
            'author': data['author_name']
        }

    def edit_metadata(self, input_path, metadata):
        output_path = f'output_{int(time.time())}.mp4'
        
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
        ffmpeg.run(stream, overwrite_output=True)
        return output_path

    def upload_to_facebook(self, video_path, metadata):
        caption = f"{metadata['description']}\n\nCredit: @{metadata['author']} #TikTok #Viral"
        
        with open(video_path, 'rb') as f:
            response = requests.post(
                f'https://graph.facebook.com/{self.fb_page_id}/video_reels',
                files={'video_file': f},
                data={
                    'access_token': self.fb_token,
                    'caption': caption,
                    'published': 'true'
                }
            )
        return response.json()

    def process_single(self, url):
        try:
            # Download
            data = self.download_tiktok(url)
            temp_path = f'temp_{int(time.time())}.mp4'
            
            with requests.get(data['video_url'], stream=True) as r:
                r.raise_for_status()
                with open(temp_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            
            # Edit metadata
            edited_path = self.edit_metadata(temp_path, data)
            
            # Upload
            upload_result = self.upload_to_facebook(edited_path, data)
            print('Upload result:', upload_result)
            
        finally:
            # Cleanup
            if os.path.exists(temp_path):
                os.remove(temp_path)
            if os.path.exists(edited_path):
                os.remove(edited_path)

if __name__ == '__main__':
    bot = TikTokAutoUploader()
    bot.listen_messages()
