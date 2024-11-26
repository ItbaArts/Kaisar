import requests
import os
from utils.logger import logger
from utils.file_handler import save_to_file
import json

def clear_files():
    """Membersihkan file tokens.txt dan id.txt"""
    try:
        # Bersihkan tokens.txt
        with open('config/tokens.txt', 'w') as f:
            f.write('')
        logger("File tokens.txt dibersihkan", 'success')
            
        # Bersihkan id.txt
        with open('config/id.txt', 'w') as f:
            f.write('')
        logger("File id.txt dibersihkan", 'success')
    except Exception as e:
        logger(f"Error saat membersihkan file: {str(e)}", 'error')

async def check_and_update_username(email, token):
    """Update nama user jika belum ada"""
    try:
        base_url = "https://zero-api.kaisar.io"
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/119.0.0.0 Safari/537.36'
        }

        # Get profile dulu untuk cek name
        response = requests.get(
            f'{base_url}/user/profile',
            headers=headers,
            timeout=10
        )
        
        if response.ok:
            data = response.json().get('data', {})
            current_name = data.get('name')
            
            # Jika name sudah ada, skip update
            if current_name:
                logger(f"Name sudah terisi: {current_name}", 'info')
                return
                
            # Jika name kosong, lakukan update
            new_name = email.split('@')[0].capitalize()
            logger(f"Mencoba update nama menjadi: {new_name}", 'debug')
            
            update_response = requests.put(
                f'{base_url}/user/profile',
                headers=headers,
                json={
                    'name': new_name
                },
                timeout=10
            )
            
            if update_response.ok:
                logger(f"Nama berhasil diupdate menjadi: {new_name}", 'success')
            else:
                error_data = update_response.json().get('error', {})
                error_msg = error_data.get('message', 'Unknown error')
                logger(f"Gagal update nama: {error_msg}", 'error')
                
    except Exception as e:
        logger(f"Error saat update nama: {str(e)}", 'error')

async def login_user(email_data):
    """Login user dengan format email|password"""
    try:
        # Split email dan password
        email, password = email_data.strip().split('|')
        
        response = requests.post(
            'https://zero-api.kaisar.io/auth/login',
            json={'email': email, 'password': password},
            headers={'Content-Type': 'application/json'}
        )
        
        if response.ok:
            data = response.json().get('data', {})
            if token := data.get('accessToken'):
                logger(f"User {email} berhasil login.", 'success')
                save_to_file('config/tokens.txt', token + '\n')
                
                # Cek dan update username setelah login berhasil
                await check_and_update_username(email, token)
                
                return token
            else:
                logger(f"Login gagal: Token tidak ditemukan", 'error')
        else:
            logger(f"Login gagal: {response.json().get('message', 'Unknown error')}", 'error')
            
    except ValueError:
        logger(f"Format email tidak valid: {email_data}", 'error')
    except Exception as e:
        logger(f"Error saat login: {str(e)}", 'error')
    return None
