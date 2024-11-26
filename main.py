import os
import json
import asyncio
from validator import BotValidator
from utils.logger import logger, clear, key_bot
from utils.file_handler import read_from_file
import register
from login import clear_files, login_user
from task import check_and_claim_task
import requests
import random
from typing import List, Optional
import time
from mining import (
    ping_and_update,
    daily_checkin,
    create_api_client,
    get_mining_data,
    claim,
    start_new_mining_task
)

def ask_user_question(query):
    return input(query).strip()

def generate_extension_ids(tokens):
    import uuid
    from utils.file_handler import save_to_file
    
    extension_ids = [str(uuid.uuid4()) for _ in tokens]
    for ext_id in extension_ids:
        save_to_file('config/id.txt', ext_id + '\n')
    logger(f"Berhasil generate {len(extension_ids)} extension ID", 'success')
    return extension_ids

def create_api_client(token, proxy=None):
    import requests
    
    session = requests.Session()
    session.headers.update({
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    })
    
    if proxy:
        session.proxies.update({
            'http': proxy,
            'https': proxy
        })
    
    # Set base URL
    class ApiClient:
        def __init__(self, session, base_url):
            self.session = session
            self.base_url = base_url.rstrip('/')
            
        def get(self, endpoint, **kwargs):
            return self.session.get(f"{self.base_url}{endpoint}", **kwargs)
            
        def post(self, endpoint, **kwargs):
            return self.session.post(f"{self.base_url}{endpoint}", **kwargs)
    
    return ApiClient(session, 'https://zero-api.kaisar.io')

def get_realtime_proxies() -> List[str]:
    """Mengambil daftar proxy secara realtime"""
    try:
        response = requests.get('https://airdrop.itbaarts.com/proxy.php?p')
        if response.ok:
            # Split dan bersihkan daftar proxy
            proxies = response.text.strip().split()
            # Filter hanya proxy yang valid (http/https/socks)
            valid_proxies = [
                proxy for proxy in proxies 
                if proxy.startswith(('http://', 'https://', 'socks4://', 'socks5://'))
            ]
            return valid_proxies
        else:
            logger("Gagal mengambil proxy realtime", 'error')
            return []
    except Exception as e:
        logger(f"Error saat mengambil proxy: {str(e)}", 'error')
        return []

class ProxyManager:
    def __init__(self):
        self.proxy_assignments = {}  # {token: {'proxy': str, 'last_update': timestamp}}
        self.proxy_update_interval = 3 * 60 * 60  # 3 jam dalam detik
        
    def should_update_proxy(self, token):
        if token not in self.proxy_assignments:
            return True
        
        current_time = time.time()
        last_update = self.proxy_assignments[token].get('last_update', 0)
        return (current_time - last_update) >= self.proxy_update_interval
        
    def update_proxies(self, tokens):
        """Update proxy untuk token yang memerlukan pembaruan"""
        tokens_need_update = [t for t in tokens if self.should_update_proxy(t)]
        if not tokens_need_update:
            return
            
        new_proxies = get_realtime_proxies()
        if not new_proxies:
            logger("Gagal mendapatkan proxy baru", 'error')
            return
            
        for token in tokens_need_update:
            if new_proxies:
                proxy = random.choice(new_proxies)
                new_proxies.remove(proxy)
                self.proxy_assignments[token] = {
                    'proxy': proxy,
                    'last_update': time.time()
                }
                logger(f"Proxy baru ditugaskan untuk token {token[:8]}...", 'info')
            else:
                logger(f"Tidak ada proxy tersedia untuk token {token[:8]}...", 'error')
                
    def get_proxy(self, token):
        """Mendapatkan proxy untuk token tertentu"""
        return self.proxy_assignments.get(token, {}).get('proxy')

async def start_mining():
    """Fungsi untuk menjalankan mining dengan proxy tetap per akun"""
    tokens = read_from_file('config/tokens.txt')
    ids = read_from_file('config/id.txt')
    
    if not all([tokens, ids]):
        logger('File token atau extension ID kosong', 'error')
        return

    proxy_manager = ProxyManager()
    max_retries = 3
    
    while True:
        logger('========= Putaran Mining Baru Dimulai =========', 'info')
        
        for i, token in enumerate(tokens):
            extension_id = ids[i % len(ids)]
            proxy = proxy_manager.get_proxy(token)
            
            if not proxy:
                new_proxies = get_realtime_proxies()
                if new_proxies:
                    proxy = random.choice(new_proxies)
                    proxy_manager.proxy_assignments[token] = {
                        'proxy': proxy,
                        'last_update': time.time()
                    }
                    logger(f"Proxy baru ditugaskan untuk token {token[:8]}...", 'info')
                else:
                    logger(f"[Akun #{i+1}] Tidak ada proxy tersedia, melewati...", 'warn')
                    continue
                
            retry_count = 0
            success = False
            
            while retry_count < max_retries and not success:
                api_client = create_api_client(token, proxy)
                logger(f"=================[Akun #{i+1}] Memulai mining =================", 'info')

                try:
                    success = await ping_and_update(api_client, extension_id)
                    if success:
                        logger(f"[Akun #{i+1}] Mining selesai", 'success')
                        break
                    else:
                        retry_count += 1
                        if retry_count < max_retries:
                            new_proxies = get_realtime_proxies()
                            if new_proxies:
                                proxy = random.choice(new_proxies)
                                proxy_manager.proxy_assignments[token] = {
                                    'proxy': proxy,
                                    'last_update': time.time()
                                }
                                logger(f"[Akun #{i+1}] Mencoba dengan proxy baru...", 'warn')
                            await asyncio.sleep(5)
                except Exception as e:
                    logger(f"[Akun #{i+1}] Mining gagal: {str(e)}", 'error')
                    retry_count += 1
                    if retry_count < max_retries:
                        new_proxies = get_realtime_proxies()
                        if new_proxies:
                            proxy = random.choice(new_proxies)
                            proxy_manager.proxy_assignments[token] = {
                                'proxy': proxy,
                                'last_update': time.time()
                            }
                            logger(f"[Akun #{i+1}] Mencoba dengan proxy baru...", 'warn')
                        await asyncio.sleep(5)
            
            if not success:
                logger(f"[Akun #{i+1}] Gagal setelah {max_retries} percobaan, melewati akun ini", 'error')
            
            await asyncio.sleep(5)
            
        logger("Menunggu 1 menit sebelum putaran berikutnya...", 'info')
        await asyncio.sleep(60)

async def complete_tasks():
    """Fungsi untuk menyelesaikan task"""
    tokens = read_from_file('config/tokens.txt')
    ids = read_from_file('config/id.txt')

    if not all([tokens, ids, proxies]):
        logger('File token, extension ID, atau proxy kosong, tidak bisa menyelesaikan task.', 'error')
        return

    logger('========= Memulai Penyelesaian Task =========', 'info')

    for i, token in enumerate(tokens):
        extension_id = ids[i % len(ids)]
        proxy = proxies[i % len(proxies)]
        api_client = create_api_client(token, proxy)

        logger(f"[Akun #{i+1}] Mengecek task...", 'info')

        try:
            await check_and_claim_task(api_client, extension_id)
            logger(f"[{extension_id}] Pengecekan task selesai.", 'success')
        except Exception as e:
            logger(f"[{extension_id}] Gagal mengecek task: {str(e)}", 'error')

async def main():
    clear()
    key_bot()
    validator = BotValidator()
    
    # Validasi awal
    if not await validator.start_validation():
        return
    
    # Jalankan validasi berkala di background
    validation_task = asyncio.create_task(validator.start_periodic_check())
    
    try:
        while True:
            clear()
            key_bot()
            
            # Cek status validasi
            if validation_task.done():
                if validation_task.result() is False:
                    # Restart bot jika validasi gagal
                    if not await validator.start_validation():
                        break
                    validation_task = asyncio.create_task(validator.start_periodic_check())
            
            choice = ask_user_question("""
Pilih operasi:
1. Register Akun Baru
2. Login Akun
3. Generate Extension ID
4. Mulai Mining
5. Selesaikan Task
6. Keluar Program
Masukkan nomor: """)

            if choice == '1':  # Register
                await register.handle_registration()
                
            elif choice == '2':  # Login
                clear()
                key_bot()
                clear_files()
                logger("Memulai proses login dengan data baru...", 'info')
                
                emails = read_from_file('config/emails.txt')
                if not emails:
                    logger('File config/emails.txt kosong, silakan tambahkan email dan coba lagi.', 'error')
                    continue

                success_count = 0
                for email_data in emails:
                    if not email_data.strip():  # Skip baris kosong
                        continue
                        
                    logger(f"Mencoba login untuk {email_data.split('|')[0]}...", 'info')
                    if await login_user(email_data):
                        success_count += 1
                        
                total_valid_accounts = len([e for e in emails if e.strip()])
                logger(f"Berhasil login {success_count} dari {total_valid_accounts} akun", 'info')
                
                if success_count > 0:
                    logger("Silakan generate Extension ID baru (Menu 3)", 'info')

            elif choice == '3':  # Generate Extension ID
                clear()
                key_bot()
                tokens = read_from_file('config/tokens.txt')
                if tokens:
                    generate_extension_ids(tokens)
                    logger('Extension ID berhasil dibuat.', 'success')
                else:
                    logger('File token kosong, silakan login terlebih dahulu.', 'error')

            elif choice == '4':  # Start Mining
                clear()
                key_bot()
                logger('Memulai proses mining...', 'info')
                await start_mining()
                
            elif choice == '5':  # Complete Tasks
                clear()
                key_bot()
                logger('Memulai penyelesaian task...', 'info')
                await complete_tasks()
                
            elif choice == '6':  # Exit
                clear()
                key_bot()
                logger('Program selesai, terima kasih!', 'info')
                break
                
            else:
                logger('Input tidak valid, silakan pilih lagi.', 'warn')

    except Exception as e:
        logger(f"Error: {str(e)}", 'error')
    finally:
        # Batalkan task validasi saat keluar
        if not validation_task.done():
            validation_task.cancel()

if __name__ == '__main__':
    asyncio.run(main())