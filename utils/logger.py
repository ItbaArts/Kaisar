from datetime import datetime
from colorama import init, Fore, Style
import requests
import json

init()  # Initialize colorama

def logger(message, level='info'):
    """Enhanced logger with colors and better formatting"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Color mapping
    colors = {
        'info': Fore.CYAN,
        'success': Fore.GREEN,
        'warn': Fore.YELLOW,
        'error': Fore.RED,
        'debug': Fore.MAGENTA
    }
    
    # Level prefix mapping
    prefixes = {
        'info': 'INFO',
        'success': 'SUCCESS',
        'warn': 'WARNING',
        'error': 'ERROR',
        'debug': 'DEBUG'
    }
    
    color = colors.get(level, Fore.WHITE)
    prefix = prefixes.get(level, 'INFO')
    
    # Format: [Timestamp] [Level] Message
    formatted_message = f"{Fore.WHITE}[{timestamp}] {color}[{prefix}] {message}{Style.RESET_ALL}"
    print(formatted_message)

def clear():
    import os
    os.system('cls' if os.name == 'nt' else 'clear')

def key_bot():
    api = "https://itbaarts.com/api_prem.json"
    try:
        response = requests.get(api)
        response.raise_for_status()
        try:
            data = response.json()
            header = data['header']
            print('\033[96m' + header + '\033[0m')
        except json.JSONDecodeError:
            print('\033[96m' + response.text + '\033[0m')
    except requests.RequestException as e:
        print('\033[96m' + f"Failed to load header: {e}" + '\033[0m')
