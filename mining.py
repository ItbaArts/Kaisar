import json
import time
from datetime import datetime
from utils.logger import logger
import aiohttp
import asyncio
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from utils.file_handler import read_from_file

async def daily_checkin(api_client, extension_id):
    """Daily checkin untuk mining"""
    try:
        response = api_client.post('/checkin/check', json={})
        
        if not response:
            return
            
        if response.ok:
            data = response.json()
            if data.get('data'):
                logger(f"Daily checkin berhasil: waktu checkin {data['data']['time']}", 'success')
            else:
                logger(f"Daily checkin gagal: {data.get('message', 'Error tidak diketahui')}", 'warn')
    except Exception as e:
        if hasattr(e, 'response') and hasattr(e.response, 'status_code') and e.response.status_code == 412:
            logger(f"Daily checkin sudah selesai hari ini.", 'info')
        else:
            pass

def create_api_client(token, proxy=None):
    """Membuat API client dengan retry dan fallback mechanism"""
    session = requests.Session()
    
    # Setup retry strategy
    retry_strategy = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[500, 502, 503, 504, 429],
        allowed_methods=["GET", "POST"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Headers
    session.headers.update({
        'Authorization': f'Bearer {token}',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/119.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    })
    
    # Coba gunakan proxy, jika gagal gunakan koneksi langsung
    if proxy:
        try:
            # Test proxy
            session.proxies = {
                'http': proxy,
                'https': proxy
            }
            test_response = session.get('https://zero-api.kaisar.io/ping', timeout=10)
            if not test_response.ok:
                logger("Proxy tidak berfungsi, menggunakan koneksi langsung", 'warn')
                session.proxies = {}
        except Exception as e:
            logger(f"Error dengan proxy: {str(e)}, menggunakan koneksi langsung", 'warn')
            session.proxies = {}
    
    class APIClient:
        def __init__(self, session):
            self.session = session
            self.base_url = 'https://zero-api.kaisar.io'
        
        def _make_request(self, method, endpoint, **kwargs):
            try:
                url = f"{self.base_url}{endpoint}"
                response = self.session.request(method, url, **kwargs)
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                logger(f"Request error: {str(e)}", 'error')
                return None
        
        def get(self, endpoint, **kwargs):
            return self._make_request('GET', endpoint, **kwargs)
            
        def post(self, endpoint, **kwargs):
            return self._make_request('POST', endpoint, **kwargs)
    
    return APIClient(session)

async def ping_and_update(api_client, extension_id):
    """Ping server dan update mining status"""
    try:
        response = api_client.post('/extension/ping', json={'extension': extension_id}, timeout=30)
        
        if not response:
            logger(f"Ping gagal: Tidak ada response", 'warn')
            return False
            
        if response.ok and response.json().get('data'):
            logger(f"Ping berhasil", 'info')
            # Tambah delay sebelum get mining data
            await asyncio.sleep(2)
            mining_data = await get_mining_data(api_client, extension_id)
            if mining_data:
                # Tambah delay sebelum daily checkin
                await asyncio.sleep(2)
                await daily_checkin(api_client, extension_id)
                return True
            return False
        else:
            error_msg = response.json().get('message', 'Unknown error') if response else "Tidak ada response"
            logger(f"Ping gagal: {error_msg}", 'warn')
            return False
    except Exception as e:
        logger(f"Error saat ping: {str(e)}", 'error')
        return False

async def check_boost_availability(api_client):
    """Cek ketersediaan boost"""
    try:
        response = api_client.get('/extension/boost-availability')
        if response and response.ok:
            data = response.json().get('data', {})
            return data.get('available', False)
        return False
    except Exception as e:
        logger(f"Error cek boost availability: {str(e)}", 'error')
        return False

async def activate_boost(api_client, extension_id):
    """Aktivasi boost mining"""
    try:
        response = api_client.post('/extension/activate-boost', json={
            'extension': extension_id
        })
        if response and response.ok:
            logger("Boost berhasil diaktifkan", 'success')
            return True
        return False
    except Exception as e:
        logger(f"Error aktivasi boost: {str(e)}", 'error')
        return False

async def get_mining_data(api_client, extension_id):
    """Get mining data dengan boost check"""
    try:
        # Cek dan aktivasi boost sebelum get mining data
        if await check_boost_availability(api_client):
            await activate_boost(api_client, extension_id)
            
        # Lanjutkan dengan kode get_mining_data yang existing
        response = api_client.get('/mining/current', params={'extension': extension_id})
        
        if not response or not response.ok:
            logger(f"Tidak ada response saat get mining data - mencoba start mining...", 'warn')
            # Coba start mining jika belum dimulai
            await start_new_mining_task(api_client, extension_id)
            # Tunggu sebentar dan coba get data lagi
            await asyncio.sleep(2)
            response = api_client.get('/mining/current', params={'extension': extension_id})
            
            if not response or not response.ok:
                logger(f"Masih tidak bisa get mining data setelah start", 'error')
                return False
            
        data = response.json()
        if not data.get('data'):
            logger(f"Data mining tidak valid", 'error')
            return False
            
        mining_data = data['data']
        
        # Update progress
        update_progress(extension_id, mining_data)
        
        # Update mining point dan cek balance
        await update_mining_point(extension_id, mining_data, api_client)
        
        if mining_data.get('ended') == 1:
            logger(f"Mining selesai, mencoba claim point...", 'debug')
            await claim(api_client, extension_id)
            # Tambahkan delay 1 menit sebelum memulai mining baru
            logger(f"Menunggu 60 detik sebelum memulai mining baru...", 'info')
            await asyncio.sleep(60)
            await start_new_mining_task(api_client, extension_id)
            
        return True
            
    except Exception as e:
        logger(f"Error saat get mining data: {str(e)}", 'error')
        return False

async def update_mining_point(extension_id, mining_data, api_client):
    """Update mining point dan cek total balance"""
    try:
        # Perbaikan perhitungan waktu
        start_time = mining_data['start']
        if isinstance(start_time, int):
            # Jika start_time dalam format timestamp
            start_timestamp = start_time
        else:
            # Jika start_time dalam format string ISO
            start_timestamp = datetime.strptime(start_time, '%Y-%m-%dT%H:%M:%S.%fZ').timestamp() * 1000
            
        current_time = time.time() * 1000
        elapsed_time_hours = (current_time - start_timestamp - mining_data['miss']) / 36e5
        points = elapsed_time_hours * mining_data['hourly']
        mining_point = max(0, points)
        
        # Cek total balance
        total_points = await check_balance(api_client, extension_id)
        
        logger(f"Total Points: {total_points}, Mining Points: {mining_point:.2f}, Waktu Mining: {elapsed_time_hours:.2f} jam", 'warn')
        
    except Exception as e:
        logger(f"Error update mining point: {str(e)}", 'error')

def update_progress(extension_id, mining_data):
    """Update progress mining dengan format waktu WITA"""
    try:
        current_time = int(time.time() * 1000)
        end_time = mining_data['end']
        remaining_time = max(0, end_time - current_time)
        
        # Konversi ke format waktu WITA
        current_wita = datetime.fromtimestamp(current_time/1000).strftime('%Y-%m-%d %H:%M:%S')
        end_wita = datetime.fromtimestamp(end_time/1000).strftime('%Y-%m-%d %H:%M:%S')
        
        # Konversi remaining time ke format jam:menit:detik
        remaining_hours = remaining_time // (1000 * 60 * 60)
        remaining_minutes = (remaining_time % (1000 * 60 * 60)) // (1000 * 60)
        remaining_seconds = (remaining_time % (1000 * 60)) // 1000
        
        logger(
            f"Progress: "
            f"Waktu Sekarang: {current_wita} WITA, "
            f"Waktu Selesai: {end_wita} WITA, "
            f"Sisa Waktu: {int(remaining_hours)}:{int(remaining_minutes):02d}:{int(remaining_seconds):02d}", 
            'warn'
        )
        
    except Exception as e:
        logger(f"Error update progress: {str(e)}", 'error')

async def claim(api_client, extension_id):
    """Claim mining rewards"""
    try:
        logger(f"Mencoba claim mining points...")
        response = api_client.post('/mining/claim', json={'extension': extension_id})
        
        if response.ok and response.json().get('data'):
            logger(f"Claim berhasil: {json.dumps(response.json()['data'])}", 'success')
            await start_new_mining_task(api_client, extension_id)
        else:
            logger(f"Claim gagal: {response.json().get('message')}", 'error')
            
    except Exception as e:
        logger(f"Error saat claim: {str(e)}", 'error')

async def start_new_mining_task(api_client, extension_id):
    """Start mining baru dengan handling error lebih baik"""
    try:
        response = api_client.post('/mining/start', json={'extension': extension_id})
        
        if response.ok:
            logger(f"Mining baru berhasil dimulai", 'success')
            return True
        else:
            error_data = response.json()
            # Cek jika mining sudah dimulai
            if response.status_code == 412 and error_data.get('error', {}).get('message') == 'Mining is started.':
                logger(f"Mining sudah berjalan, skip proses start", 'info')
                return True
            else:
                logger(f"Mining baru gagal dimulai: {error_data.get('message')}", 'error')
                return False
                
    except Exception as e:
        logger(f"Error saat memulai mining baru: {str(e)}", 'error')
        return False

async def check_balance(api_client, extension_id):
    """Cek total balance user"""
    try:
        logger(f"Mengecek balance points...")
        response = api_client.get('/user/balances')
        
        if response.ok and response.json().get('data'):
            balance = response.json()['data'][0]['balance']
            logger(f"Balance: {balance}", 'info')
            return balance
            
        return None
        
    except Exception as e:
        logger(f"Error cek balance: {str(e)}", 'error')
        return None

async def start_mining():
    """Fungsi untuk menjalankan semua akun bersamaan dengan proxy berbeda"""
    tokens = read_from_file('config/tokens.txt')
    ids = read_from_file('config/id.txt')
    proxies = get_realtime_proxies()  # Ambil proxy dari server

    if not all([tokens, ids, proxies]):
        logger('File token, extension ID atau proxy kosong.', 'error')
        return

    logger('\n' + '='*50, 'info')
    logger('🚀 MENJALANKAN SEMUA AKUN BERSAMAAN', 'info')
    logger('='*50 + '\n', 'info')

    # Jalankan semua akun dalam satu batch
    tasks = []
    for i, (token, proxy) in enumerate(zip(tokens, proxies)):
        extension_id = ids[i % len(ids)]
        api_client = create_api_client(token, proxy=proxy)  # Gunakan proxy untuk setiap akun
        tasks.append(process_single_account(i, api_client, extension_id))

    # Eksekusi semua akun bersamaan
    await asyncio.gather(*tasks)

async def process_single_account(index, api_client, extension_id):
    """Proses untuk satu akun"""
    try:
        logger(f"📱 AKUN #{index+1} [{extension_id[:8]}...]", 'info')
        
        # Jalankan semua operasi untuk satu akun
        success = await ping_and_update(api_client, extension_id)
        if success:
            await daily_checkin(api_client, extension_id)
            
        # Cek dan aktivasi boost
        if await check_boost_availability(api_client):
            await activate_boost(api_client, extension_id)
            
        logger(f"✅ AKUN #{index+1} [{extension_id[:8]}...] Selesai", 'success')
        
    except Exception as e:
        logger(f"❌ AKUN #{index+1} [{extension_id[:8]}...] Error: {str(e)}", 'error')

def get_realtime_proxies():
    """Mengambil daftar proxy dari server"""
    try:
        response = requests.get('https://airdrop.itbaarts.com/proxy.php?p')
        if response.ok:
            proxies = response.text.strip().split()
            # Filter proxy yang valid
            valid_proxies = [
                proxy for proxy in proxies 
                if proxy.startswith(('http://', 'https://', 'socks4://', 'socks5://'))
            ]
            logger(f"Berhasil mendapatkan {len(valid_proxies)} proxy", 'success')
            return valid_proxies
        else:
            logger("Gagal mengambil proxy dari server", 'error')
            return []
    except Exception as e:
        logger(f"Error saat mengambil proxy: {str(e)}", 'error')
        return []
