import random
import string
import time
import requests
import json
from bs4 import BeautifulSoup
from utils.logger import logger, clear, key_bot
from utils.file_handler import save_to_file
from requests.adapters import HTTPAdapter
from validator import BotValidator
from urllib3.util.retry import Retry

indonesian_names = [
    "Aditya", "Aisyah", "Amanda", "Andini", "Anggun", "Anggita", "Annisa", "Ariana", "Ashari",
    "Abimana", "Abimata", "Abirama", "Abiresa", "Adeline", "Adhitya", "Adiarja", "Adibrata", "Adikara",
    "Adinata", "Aditama", "Adriana", "Adwinta", "Agastya", "Aghania", "Agnesia", "Agustina", "Ahimsa",
    "Ainiyah", "Airlangga", "Aisyiah", "Ajendra", "Ajengan", "Akasaka", "Alamanda", "Alandra", "Aldebaran",
    "Aleandra", "Alethea", "Alexandra", "Alfiana", "Alindra", "Almaira", "Almeira", "Almyra", "Alodya",
    "Aloysius", "Alphanya", "Althafun", "Alviana", "Alyshia", "Amadeus", "Amandita", "Amartha", "Amartya",
    "Amelia", "Amelina", "Anargya", "Anastasia", "Andara", "Andhika", "Andika", "Andreana", "Angelica",
    "Angelina", "Angelia", "Anindita", "Anindya", "Anjani", "Annora", "Antaresa", "Anthonia", "Aprilia",
    "Arahita", "Arandea", "Ardhana", "Ardiana", "Arentha", "Ariadne", "Arianti", "Arifina", "Arimbi",
    "Arjuna", "Arkana", "Armadea", "Armina", "Arnetta", "Arsyifa", "Artemia", "Arthana", "Arundati",
    "Arvania", "Asadela", "Ashanty", "Ashilla", "Askara", "Asmarani", "Asmara", "Asteria", "Asterina",
    "Astinia", "Aswarini", "Athalia", "Athallah", "Athaya", "Athenia", "Athifah", "Athirah", "Atmaja",
    "Audhina", "Audrey", "Aurelia", "Aurellia", "Aurora", "Avalina", "Avantika", "Averina", "Avicenna",
    "Ayesha", "Ayudya", "Azalea", "Azalia", "Azarine", "Azkiya", "Azriel", "Azzahra", "Azzura",
    "Bagaskoro", "Bagawanta", "Baghiza", "Bahagia", "Bahtera", "Baktiar", "Balqies", "Balqis", "Bambang",
    "Banendra", "Barata", "Baruna", "Basudewa", "Batara", "Bathara", "Bayuaji", "Bayuwangi", "Belinda",
    "Beningati", "Bentara", "Berlianna", "Berliani", "Bernadin", "Bethari", "Betharia", "Bhadrika",
    "Bhanuwati", "Bhanuaji", "Bharata", "Bhirawa", "Bhisana", "Bhisma", "Bhumiaji", "Bhumika", "Bianda",
    "Biandra", "Bidadari", "Bidari", "Bijaya", "Binangkit", "Bintan", "Bintang", "Biruni", "Bramanta",
    "Bramanti", "Brawijaya", "Budiarta", "Budiman", "Budianto", "Bulandari", "Burhani", "Busaina",
    "Cakrawala", "Cakrayuda", "Calista", "Callysta", "Camelia", "Candida", "Candrika", "Carissa",
    "Carmelia", "Carolina", "Cassandra", "Catharina", "Cattleya", "Cempaka", "Chandani", "Chandra",
    "Chandrika", "Charissa", "Chelsea", "Chesilia", "Chiara", "Chintami", "Chintana", "Chintya",
    "Chrysant", "Chrysanta", "Cinthya", "Citrawati", "Clarissa", "Claudia", "Cordelia", "Cornelia",
    "Yustisia", "Zabrina", "Zafirah", "Zahirah", "Zalikha", "Zamira", "Zaneta", "Zanitha", "Zavira",
    "Zelinda", "Zenitha", "Zerlina", "Zharifa", "Zhafira", "Zhalfa", "Zhafirah", "Zhafarina", "Zhevania",
    "Zivanna", "Zulaikha", "Zulayha", "Zuleyka", "Zulfikar", "Zulhijah", "Zumaira", "Zumarni", "Zuwaina"
]

def create_session():
    """Membuat session dengan retry strategy"""
    session = requests.Session()
    
    # Setup retry strategy
    retry_strategy = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[500, 502, 503, 504],
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Headers yang diperlukan
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/119.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Content-Type': 'application/json',
        'Origin': 'https://zero.kaisar.io',
        'Referer': 'https://zero.kaisar.io/register'
    })
    
    return session

async def register_user(email, password, invite_code=None):
    """Register user menggunakan form di website"""
    try:
        session = create_session()
        
        # Data untuk registrasi dengan format yang benar
        register_data = {
            'email': email,
            'password': password,
            'referrer': invite_code or get_referral_code()  # Menggunakan 'referrer' bukan 'inviteCode'
        }
        
        logger(f"Mengirim data registrasi: {register_data}", 'info')
        logger("Menunggu respon server (bisa memakan waktu 1-2 menit)...", 'info')
        
        response = session.post(
            'https://zero-api.kaisar.io/auth/register',
            json=register_data,
            timeout=180
        )
        
        logger(f"Status code: {response.status_code}", 'info')
        
        if response.ok:
            logger(f"User {email} berhasil register!", 'success')
            return True
        else:
            try:
                error_data = response.json()
                error_message = error_data.get('message', 'Unknown error')
                logger(f"Register gagal: {error_message}", 'error')
            except:
                logger(f"Register gagal dengan status code: {response.status_code}", 'error')
            return False
                
    except requests.exceptions.Timeout:
        logger("Timeout setelah menunggu 3 menit. Server mungkin sedang sibuk.", 'error')
        return False
    except Exception as e:
        logger(f"Error saat register: {str(e)}", 'error')
        return False

def generate_random_email(domain="pokemail.net"):
    """Generate random email dengan nama Indonesia + 3-5 angka random dan return password-nya"""
    name = random.choice(indonesian_names)
    num_digits = random.randint(3, 5)
    numbers = ''.join(random.choices(string.digits, k=num_digits))
    
    email = f"{name.lower()}{numbers}@{domain}"
    # Generate password dari nama dan angka dengan format Nama123@
    password = f"{name}{numbers}@"
    
    return email, password

async def register_multiple_accounts():
    """Fungsi untuk register multiple accounts"""
    validator = BotValidator()
    last_check = time.time()
    
    try:
        num_accounts = int(input("\nBerapa akun yang ingin dibuat? "))
        
        success_count = 0
        for i in range(num_accounts):
            # Cek validasi setiap 30 detik
            current_time = time.time()
            if current_time - last_check >= 30:
                if not await validator.periodic_check():
                    return
                last_check = current_time

            email, password = generate_random_email()
            logger(f"\nMembuat akun ke-{i+1} dengan email: {email}", 'info')
            
            if await register_user(email, password):
                # Tunggu email verifikasi
                logger("Menunggu email verifikasi (max 60 detik)...", 'info')
                verify_url = get_verify_link(email)
                
                if verify_url:
                    if await verify_email(email, verify_url):
                        save_to_file('config/emails.txt', f"{email}|{password}\n")
                        success_count += 1
                        logger(f"Kredensial disimpan: {email}|{password}", 'success')
                else:
                    logger(f"Tidak menemukan link verifikasi untuk {email}", 'error')
            
            # Tunggu sebelum mencoba akun berikutnya
            if i < num_accounts - 1:
                logger("Menunggu 10 detik sebelum membuat akun berikutnya...", 'info')
                time.sleep(10)
                    
        logger(f"\nBerhasil membuat {success_count} dari {num_accounts} akun", 'success')
        
    except ValueError:
        logger("Jumlah akun harus berupa angka", 'error')
    except Exception as e:
        logger(f"Error saat membuat akun: {str(e)}", 'error')

def setup_guerrilla_mail(email):
    """Setup GuerrillaMail session"""
    try:
        session = requests.Session()
        
        # Set email di GuerrillaMail
        set_email_url = "https://api.guerrillamail.com/ajax.php"
        params = {
            'f': 'set_email_user',
            'email_user': email.split('@')[0],
            'domain': 'pokemail.net'
        }
        
        response = session.get(set_email_url, params=params)
        if response.ok:
            logger(f"Berhasil setup email {email}", 'success')
            return session
        else:
            logger("Gagal setup GuerrillaMail", 'error')
            return None
            
    except Exception as e:
        logger(f"Error setup GuerrillaMail: {str(e)}", 'error')
        return None

def get_verify_link(email):
    """Fungsi untuk mendapatkan link verifikasi dari email"""
    try:
        session = setup_guerrilla_mail(email)
        if not session:
            return None
            
        # Tunggu dan cek email (max 60 detik)
        for _ in range(12):  # 12 x 5 detik = 60 detik
            response = session.get(
                "https://api.guerrillamail.com/ajax.php",
                params={'f': 'get_email_list', 'offset': 0}
            )
            
            if response.ok:
                emails = response.json().get('list', [])
                for mail in emails:
                    # Cek email dari Kaisar Zero
                    if 'no-reply@kaisar.io' in mail.get('mail_from', ''):
                        email_id = mail.get('mail_id')
                        content_response = session.get(
                            "https://api.guerrillamail.com/ajax.php",
                            params={'f': 'fetch_email', 'email_id': email_id}
                        )
                        
                        if content_response.ok:
                            content = content_response.json().get('mail_body', '')
                            logger("Email verifikasi ditemukan", 'success')
                            
                            # Cari tombol "Confirm Email"
                            if 'Confirm Email' in content:
                                # Ambil URL dari tombol
                                start = content.find('href="') + 6
                                end = content.find('"', start)
                                verify_url = content[start:end]
                                logger(f"Link verifikasi ditemukan.", 'success')
                                return verify_url
                            else:
                                logger("Link verifikasi tidak ditemukan dalam email", 'error')
                                return None
            
            logger("Menunggu email verifikasi...", 'info')
            time.sleep(5)
            
        logger("Timeout menunggu email verifikasi", 'error')
        return None
        
    except Exception as e:
        logger(f"Error saat mengecek email: {str(e)}", 'error')
        return None

async def verify_email(email, verify_url):
    """Verifikasi email dengan mengakses URL verifikasi"""
    try:
        session = create_session()
        logger(f"Mengakses link verifikasi.", 'info')
        
        response = session.get(verify_url)
        
        if response.ok:
            logger(f"Email {email} berhasil diverifikasi", 'success')
            return True
        else:
            logger(f"Gagal verifikasi email. Status: {response.status_code}", 'error')
            return False
            
    except Exception as e:
        logger(f"Error saat verifikasi email: {str(e)}", 'error')
        return False

def create_session_with_proxy():
    """Membuat session dengan proxy dari server"""
    session = requests.Session()
    
    # Setup retry strategy
    retry_strategy = Retry(
        total=5,  # total retry
        backoff_factor=0.5,  # waktu tunggu antara retry
        status_forcelist=[500, 502, 503, 504, 429],
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Headers yang lebih lengkap
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/119.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Content-Type': 'application/json',
        'Origin': 'https://zero.kaisar.io',
        'Referer': 'https://zero.kaisar.io/register',
        'Connection': 'keep-alive'
    })
    
    try:
        # Ambil proxy dari server
        response = requests.get('https://airdrop.itbaarts.com/proxy.php?p')
        if response.ok:
            proxies = response.text.strip().split()
            socks5_proxies = [p for p in proxies if p.startswith('socks5://')]
            
            if socks5_proxies:
                proxy = random.choice(socks5_proxies)
                session.proxies = {'http': proxy, 'https': proxy}
                logger(f"Berhasil menggunakan proxy dari server", 'success')
                return session
    except:
        pass
    
    # Jika gagal mengambil proxy, gunakan koneksi langsung
    logger("Gagal mendapatkan proxy, menggunakan koneksi langsung", 'warn')
    session.proxies = {}
    return session

def get_saved_credentials():
    """Fungsi untuk membaca kredensial tersimpan"""
    try:
        lines = read_from_file('config/emails.txt')
        credentials = []
        for line in lines:
            if '|' in line:
                email, password = line.split('|', 1)
                credentials.append((email.strip(), password.strip()))
        return credentials
    except Exception as e:
        logger(f"Error membaca kredensial: {str(e)}", 'error')
        return []

def get_referral_code():
    """Fungsi untuk membaca kode referral dari file"""
    try:
        with open('config/reff.txt', 'r') as f:
            code = f.read().strip()
            return code if code else 'SBpUYg936'  # Menggunakan kode referral default yang baru
    except FileNotFoundError:
        # Jika file tidak ada, buat baru dengan kode default
        with open('config/reff.txt', 'w') as f:
            f.write('SBpUYg936')
        return 'SBpUYg936'
    except Exception as e:
        logger(f"Error saat membaca kode referral: {str(e)}", 'error')
        return 'SBpUYg936'

async def register_multiple_users():
    """Fungsi untuk register multiple users dari kredensial tersimpan"""
    credentials = get_saved_credentials()
    if not credentials:
        logger('Tidak ada kredensial tersimpan. Silakan input email dan password terlebih dahulu.', 'error')
        return False

    success_count = 0
    for email, password in credentials:
        logger(f"Memproses registrasi untuk {email}...", 'info')
        if await register_user(email, password):
            success_count += 1

    if success_count > 0:
        logger(f"Berhasil register {success_count} dari {len(credentials)} akun.", 'success')
    else:
        logger("Tidak ada akun yang berhasil diregister.", 'warn')

    return success_count > 0

def validate_password(password):
    """Fungsi untuk validasi password"""
    if not password:
        logger('Password tidak boleh kosong.', 'error')
        return False
        
    if len(password.strip()) < 8:
        logger('Password harus minimal 8 karakter.', 'error')
        return False
        
    return True

def handle_referral_code():
    """Fungsi untuk menangani kode referral"""
    try:
        # Tampilkan kode referral saat ini
        current_code = get_referral_code()
        logger(f"\nKode referral saat ini: {current_code}", 'info')
        
        invite_code = input("\nMasukkan kode referral baru (kosongkan untuk default): ").strip()
        
        if invite_code:
            # Hapus isi file lama dan tulis kode baru
            with open('config/reff.txt', 'w') as f:
                f.write(invite_code)
            logger("Kode referral baru berhasil disimpan", 'success')
        else:
            # Jika input kosong, gunakan default dan hapus file
            with open('config/reff.txt', 'w') as f:
                f.write('SBpUYg936')
            logger("Menggunakan kode referral default: SBpUYg936", 'info')
            
    except Exception as e:
        logger(f"Error saat mengubah kode referral: {str(e)}", 'error')

async def handle_registration():
    """Fungsi utama untuk menangani proses registrasi"""
    while True:
        clear()
        key_bot()
        logger("\n=== Menu Registrasi ===", 'info')
        choice = input("""
1. Input kode referral
2. Buat akun baru (Auto Email)
3. Kembali ke menu utama
Pilih menu (1-3): """).strip()
        
        if choice == '1':
            handle_referral_code()
            continue
        elif choice == '2':
            await register_multiple_accounts()
            continue
        elif choice == '3':
            return None
        else:
            logger("Pilihan tidak valid", 'warn')

# Pastikan semua fungsi yang diperlukan sudah diexport
__all__ = [
    'handle_registration',
    'register_multiple_accounts',
    'register_user',
    'handle_referral_code',
    'get_referral_code',
    'generate_random_email'
]
