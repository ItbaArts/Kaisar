import requests
import random
import time
import os
from utils.logger import logger
from datetime import datetime
import asyncio
import aiohttp

class BotValidator:
    def __init__(self):
        self.password = None
        self.random_code = None
        self.base_url = "https://airdrop.itbaarts.com"
        self.session = None
        
    def get_passwords(self):
        """Mengambil daftar password dari server"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/119.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            }
            
            response = requests.get(
                f"{self.base_url}/password.php",
                headers=headers,
                timeout=10
            )
            
            if response.ok:
                passwords = []
                current_date = datetime.now()
                
                for line in response.text.strip().split('\n'):
                    if '|' in line:
                        parts = line.strip().split('|')
                        password = parts[0].strip()
                        expiry_date = datetime.strptime(parts[1].strip(), '%d/%m/%Y')
                        
                        if current_date <= expiry_date:
                            passwords.append(password)
                        else:
                            pass
                        
                if passwords:
                    return passwords
                else:
                    logger("Tidak ada password aktif yang ditemukan", 'error')
                    return []
                
            else:
                logger(f"Server returned error status: {response.status_code}", 'error')
                return []
                
        except requests.exceptions.Timeout:
            logger("Timeout saat mengakses server password", 'error')
            return []
        except requests.exceptions.ConnectionError:
            logger("Tidak dapat terhubung ke server password", 'error')
            return []
        except Exception as e:
            logger(f"Error tidak terduga saat mengambil password: {str(e)}", 'error')
            return []

    def generate_random_code(self):
        """Generate 6 digit random code"""
        return ''.join(random.choices('0123456789', k=6))

    def send_random_code(self):
        """Kirim kode random ke server"""
        try:
            self.random_code = self.generate_random_code()
            url = f"{self.base_url}/change.php"
            params = {
                'password': self.password,
                'bot': 'Kaisar',
                'code': self.random_code
            }
            response = requests.get(url, params=params)
            return response.ok
        except Exception as e:
            logger(f"Error mengirim kode: {str(e)}", 'error')
            return False

    async def verify_code(self):
        """Verifikasi kode dari server"""
        try:
            url = f"{self.base_url}/index.php"
            params = {
                'password': self.password,
                'bot': 'Kaisar',
                'code': self.random_code
            }
            
            # Tutup session lama
            await self.close_session()
            
            # Buat session baru dengan headers yang lebih lengkap
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/119.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
            
            connector = aiohttp.TCPConnector(limit=50, force_close=True, ssl=False)
            self.session = aiohttp.ClientSession(connector=connector, headers=headers)
            
            # Lakukan beberapa kali percobaan jika response tidak sesuai
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    async with self.session.get(url, params=params, timeout=10) as response:
                        if response.status == 200:
                            server_code = (await response.text()).strip()
                            
                            # Tambah delay kecil untuk stabilitas
                            await asyncio.sleep(0.5)
                            
                            if server_code == self.random_code:
                                logger(f"Verifikasi berhasil (attempt {attempt + 1})", 'success')
                                return True
                            else:
                                # Jika kode tidak cocok, coba kirim ulang kode
                                if attempt < max_retries - 1:
                                    logger(f"Kode tidak cocok, mencoba kirim ulang... (attempt {attempt + 1})", 'warn')
                                    if self.send_random_code():  # Kirim kode baru
                                        await asyncio.sleep(1)  # Tunggu sebentar sebelum verifikasi ulang
                                        continue
                                else:
                                    logger(f"Kode tidak cocok setelah {max_retries} percobaan", 'error')
                                    return False
                        
                        logger(f"Response tidak ok: {response.status}", 'error')
                        
                except asyncio.TimeoutError:
                    if attempt < max_retries - 1:
                        logger(f"Timeout, mencoba lagi... (attempt {attempt + 1})", 'warn')
                        await asyncio.sleep(1)
                        continue
                    else:
                        logger("Timeout setelah beberapa percobaan", 'error')
                        return False
                        
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger(f"Error, mencoba lagi... (attempt {attempt + 1}): {str(e)}", 'warn')
                        await asyncio.sleep(1)
                        continue
                    else:
                        raise
                        
            return False
                
        except Exception as e:
            logger(f"Error verifikasi kode: {str(e)}", 'error')
            return False
        finally:
            await self.close_session()

    async def close_session(self):
        """Tutup session jika ada"""
        if self.session is not None and not self.session.closed:
            await self.session.close()
            self.session = None

    def validate_files(self):
        """Validasi keberadaan file yang diperlukan"""
        required_files = [
            'config/emails.txt',
            'config/tokens.txt',
            'config/id.txt',
            'config/reff.txt'
        ]
        
        missing_files = []
        for file in required_files:
            if not os.path.exists(file):
                missing_files.append(file)
                
        if missing_files:
            logger("File yang diperlukan tidak ditemukan:", 'error')
            for file in missing_files:
                logger(f"- {file}", 'error')
            return False
        return True

    async def start_validation(self):
        """Memulai proses validasi"""
        if not self.validate_files():
            return False

        while True:
            # Ambil daftar password
            passwords = self.get_passwords()
            if not passwords:
                logger("Tidak dapat mengambil daftar password dari server", 'error')
                return False

            # Minta input password
            self.password = input("\nMasukkan password: ").strip()
            if self.password not in passwords:
                logger("Password tidak valid!", 'error')
                continue

            # Generate dan kirim kode random
            self.random_code = self.generate_random_code()
            if not self.send_random_code():
                logger("Gagal mengirim kode random", 'error')
                continue

            # Verifikasi kode
            if await self.verify_code():
                logger("Validasi berhasil! Memulai bot...", 'success')
                return True
            
            logger("Validasi gagal, coba lagi", 'error')

    async def start_periodic_check(self):
        """Memulai pengecekan berkala"""
        while True:
            try:
                if not await self.periodic_check():
                    logger("Validasi gagal dalam periodic check", 'error')
                    return False
                await asyncio.sleep(30)  # Tunggu 30 detik sebelum check berikutnya
            except Exception as e:
                logger(f"Error dalam periodic check: {str(e)}", 'error')
                return False

    async def periodic_check(self):
        """Fungsi untuk melakukan pengecekan berkala"""
        try:
            # Tambah delay sebelum verifikasi
            await asyncio.sleep(1)
            
            if not await self.verify_code():
                # Coba beberapa kali dengan interval lebih lama
                for i in range(3):
                    await asyncio.sleep(3)  # Tunggu lebih lama antara percobaan
                    logger(f"Mencoba verifikasi ulang ({i+1}/3)...", 'warn')
                    
                    # Kirim ulang kode sebelum verifikasi
                    if self.send_random_code():
                        await asyncio.sleep(1)
                        if await self.verify_code():
                            logger("Verifikasi ulang berhasil", 'success')
                            return True
                            
                logger("Kode tidak valid setelah beberapa percobaan! Bot akan dihentikan...", 'error')
                return False
            return True
            
        except Exception as e:
            logger(f"Error saat verifikasi kode: {str(e)}", 'error')
            return False 