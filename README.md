**Panduan Instalasi:**

1. **Instal dependensi:**
```bash
sudo apt update
sudo apt install -y python3-pip chromium-chromedriver ffmpeg
pip3 install selenium requests ffmpeg-python python-dotenv webdriver-manager
```

2. **Buat file .env:**
```env
FB_PAGE_ID=idpagemu
FB_PAGE_TOKEN=tokenmu
```

3. **Buat direktori:**
```bash
mkdir -p sessions
```

4. **Jalankan:**
```bash
python3 main.py
```

**Fitur:**
1. Support single dan batch download
2. Auto-edit metadata
3. Upload ke Facebook Reels
4. Bot WhatsApp dengan session management
5. Error handling dasar
6. Cleanup file otomatis

**Catatan:**
- Pastikan sudah login WhatsApp Web sebelumnya
- Scan QR code saat pertama kali running
- Untuk server tanpa GUI, tambahkan opsi `--headless` di Chrome Options
- Sesuaikan delay sesuai kebutuhan API Facebook
