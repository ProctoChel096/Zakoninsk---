# server.py
import json
import threading
from flask import Flask, render_template, request, jsonify
import win32gui
import win32con
import win32process
import psutil
import time
import win32api
import keyboard
import os

app = Flask(__name__)

APP_VERSION = '24.08.26#001-STABLE'
SETTINGS_FILE = 'settings.json'

with open('data.json', 'r', encoding='utf-8') as f:
    LAW_DATA = json.load(f)

DEFAULT_SETTINGS = {
    'opacity': 0.85,
    'is_minimized': False,
    'hotkey': 'f9',
    'is_dragging': False,
    'is_interacting': False,
    'window_x': 100,
    'window_y': 100,
    'window_width': 500,
    'window_height': 600
}

def load_settings():
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                saved_settings = json.load(f)
                for key in DEFAULT_SETTINGS:
                    if key in saved_settings:
                        DEFAULT_SETTINGS[key] = saved_settings[key]
    except Exception as e:
        print(f"Error loading settings: {e}")
    return DEFAULT_SETTINGS.copy()

def save_settings_to_file():
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(SETTINGS, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving settings: {e}")

SETTINGS = load_settings()

def extract_penalties(data):
    penalties = []
    
    def recursive_extract(obj, section_name=''):
        if isinstance(obj, list):
            for item in obj:
                if isinstance(item, dict) and item.get('наказание'):
                    penalty_item = item.copy()
                    penalty_item['_section'] = section_name
                    penalties.append(penalty_item)
                elif isinstance(item, dict):
                    recursive_extract(item, section_name)
                elif isinstance(item, list):
                    recursive_extract(item, section_name)
        elif isinstance(obj, dict):
            for key, value in obj.items():
                if key == 'заголовок':
                    section_name = value
                recursive_extract(value, section_name)
    
    recursive_extract(data)
    
    unique_penalties = []
    seen = set()
    for penalty in penalties:
        key = json.dumps(penalty, ensure_ascii=False)
        if key not in seen:
            seen.add(key)
            unique_penalties.append(penalty)
    
    return unique_penalties

@app.route('/')
def index():
    return render_template('index.html', app_version=APP_VERSION)

@app.route('/api/version')
def get_version():
    return jsonify({'version': APP_VERSION})

@app.route('/api/penalties')
def get_penalties():
    penalties = extract_penalties(LAW_DATA)
    return jsonify(penalties)

@app.route('/api/search_penalties')
def search_penalties():
    query = request.args.get('q', '').lower()
    penalties = extract_penalties(LAW_DATA)
    
    if not query:
        return jsonify(penalties)
    
    filtered = []
    for penalty in penalties:
        searchable = json.dumps(penalty, ensure_ascii=False).lower()
        if query in searchable:
            filtered.append(penalty)
    
    return jsonify(filtered)

@app.route('/api/settings', methods=['GET', 'POST'])
def handle_settings():
    global SETTINGS
    
    if request.method == 'POST':
        data = request.json
        if data:
            SETTINGS.update(data)
            save_settings_to_file()
            return jsonify({'success': True, 'settings': SETTINGS})
    
    return jsonify(SETTINGS)

@app.route('/api/minimize')
def minimize_window():
    global SETTINGS
    SETTINGS['is_minimized'] = True
    save_settings_to_file()
    return jsonify({'success': True})

@app.route('/api/maximize')
def maximize_window():
    global SETTINGS
    SETTINGS['is_minimized'] = False
    save_settings_to_file()
    return jsonify({'success': True})

@app.route('/api/gta_status')
def gta_status():
    # Проверяем наличие GTA5
    def find_gta_window():
        def enum_windows_callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                window_text = win32gui.GetWindowText(hwnd)
                if any(name in window_text.lower() for name in ['gta5', 'gta 5', 'grand theft auto v', 'grand theft auto']):
                    try:
                        _, pid = win32process.GetWindowThreadProcessId(hwnd)
                        process = psutil.Process(pid)
                        if 'gta' in process.name().lower():
                            windows.append(hwnd)
                    except:
                        pass
            return True
        
        windows = []
        win32gui.EnumWindows(enum_windows_callback, windows)
        return windows[0] if windows else None
    
    gta_hwnd = find_gta_window()
    return jsonify({'found': gta_hwnd is not None})

@app.route('/api/close_window')
def close_window():
    save_settings_to_file()
    os._exit(0)
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False, threaded=True)