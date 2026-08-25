import json
import threading
import webview
from flask import Flask, render_template, request, jsonify
import win32gui
import win32con
import time
import ctypes
import keyboard
import os
import sys
import logging
import socket
import tkinter as tk
from tkinter import ttk
import requests

# Константы в начале
APP_VERSION = '25.08.26#006-STABLE'
REMOTE_BASE_URL = 'https://53c18a72091d.hosting.myjino.ru/Zakoninsk/lists/'

def setup_logging():
    if getattr(sys, 'frozen', False):
        log_file = os.path.join(os.path.dirname(sys.executable), 'app.log')
    else:
        log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.log')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# Окно загрузки
class LoadingWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Законинск")
        self.root.geometry("300x150")
        self.root.resizable(False, False)
        self.root.overrideredirect(True)
        self.root.configure(bg='#1a1a1a')
        
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - 300) // 2
        y = (screen_height - 150) // 2
        self.root.geometry(f"300x150+{x}+{y}")
        
        top_bar = tk.Frame(self.root, bg='#cc0000', height=3)
        top_bar.pack(side='top', fill='x')
        
        title_frame = tk.Frame(self.root, bg='#1a1a1a')
        title_frame.pack(fill='x', pady=(15, 5))
        
        title_label = tk.Label(
            title_frame, 
            text="Законинск", 
            font=('Segoe UI', 16, 'bold'),
            fg='#ffffff',
            bg='#1a1a1a'
        )
        title_label.pack()
        
        version_label = tk.Label(
            title_frame,
            text=APP_VERSION,
            font=('Segoe UI', 9),
            fg='#888888',
            bg='#1a1a1a'
        )
        version_label.pack()
        
        self.status_label = tk.Label(
            self.root,
            text="Запуск...",
            font=('Segoe UI', 11),
            fg='#ff4444',
            bg='#1a1a1a'
        )
        self.status_label.pack(pady=(5, 5))
        
        style = ttk.Style()
        style.theme_use('clam')
        style.configure(
            "Red.Horizontal.TProgressbar",
            troughcolor='#2a2a2a',
            background='#cc0000',
            bordercolor='#2a2a2a',
            lightcolor='#cc0000',
            darkcolor='#cc0000'
        )
        
        self.progress = ttk.Progressbar(
            self.root,
            style="Red.Horizontal.TProgressbar",
            length=250,
            mode='indeterminate'
        )
        self.progress.pack(pady=(5, 10))
        self.progress.start(15)
        
        copyright_label = tk.Label(
            self.root,
            text="media by: EG | created by: prostochel096",
            font=('Segoe UI', 8),
            fg='#555555',
            bg='#1a1a1a'
        )
        copyright_label.pack(side='bottom', pady=5)
    
    def update_status(self, text):
        try:
            if self.root and self.root.winfo_exists():
                self.status_label.config(text=text)
                self.root.update_idletasks()
                self.root.update()
        except:
            pass
    
    def close(self):
        try:
            if self.root:
                self.progress.stop()
                self.root.quit()
                self.root.destroy()
        except:
            pass

if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, 
            template_folder=os.path.join(BASE_DIR, 'templates'),
            static_folder=os.path.join(BASE_DIR, 'static'))

# Файлы для локального кэша
if getattr(sys, 'frozen', False):
    SETTINGS_FILE = os.path.join(os.path.dirname(sys.executable), 'settings.json')
    FAVORITES_FILE = os.path.join(os.path.dirname(sys.executable), 'favorites.json')
    CACHE_DIR = os.path.join(os.path.dirname(sys.executable), 'cache')
else:
    SETTINGS_FILE = os.path.join(BASE_DIR, 'settings.json')
    FAVORITES_FILE = os.path.join(BASE_DIR, 'favorites.json')
    CACHE_DIR = os.path.join(BASE_DIR, 'cache')

# Создаем директорию для кэша
os.makedirs(CACHE_DIR, exist_ok=True)

CACHE_FILES = {
    'DK': os.path.join(CACHE_DIR, 'DK.json'),
    'miranda': os.path.join(CACHE_DIR, 'miranda.json'),
    'tips': os.path.join(CACHE_DIR, 'tips.json')
}

def load_remote_json(filename):
    """Загружает JSON с удаленного сервера или из кэша"""
    cache_file = CACHE_FILES.get(filename)
    remote_url = f"{REMOTE_BASE_URL}{filename}.json"
    
    try:
        # Пробуем загрузить с сервера
        logger.info(f"Loading {filename}.json from remote server...")
        response = requests.get(remote_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Сохраняем в кэш
            if cache_file:
                try:
                    with open(cache_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    logger.info(f"{filename}.json cached successfully")
                except Exception as e:
                    logger.error(f"Error caching {filename}.json: {e}")
            
            return data
        else:
            logger.warning(f"Remote server returned {response.status_code} for {filename}.json")
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error loading {filename}.json from remote: {e}")
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing {filename}.json from remote: {e}")
    
    # Если не удалось загрузить с сервера, пробуем кэш
    if cache_file and os.path.exists(cache_file):
        try:
            logger.info(f"Loading {filename}.json from cache...")
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading {filename}.json from cache: {e}")
    
    # Возвращаем данные по умолчанию
    logger.warning(f"Using default data for {filename}.json")
    return get_default_data(filename)

def get_default_data(filename):
    """Возвращает данные по умолчанию для разных файлов"""
    if filename == 'DK':
        return {"кодекс": "Дорожный кодекс России Онлайн", "версия": APP_VERSION, "главы": []}
    elif filename == 'miranda':
        return {
            "text": "Вы имеете право хранить молчание. Всё, что вы скажете, может быть использовано против вас в суде. Вы имеете право на адвоката. Если вы не можете позволить себе адвоката, он будет предоставлен вам бесплатно."
        }
    elif filename == 'tips':
        return [
            {"text": "Всегда зачитывайте права Миранды при задержании"},
            {"text": "Проверяйте документы у подозреваемого"},
            {"text": "Не забывайте про ордер на обыск"},
            {"text": "Фиксируйте все доказательства"},
            {"text": "Соблюдайте процедуру ареста"}
        ]
    return {}

# Загрузка данных с сервера
logger.info("Loading data from remote server...")
LAW_DATA = load_remote_json('DK')
MIRANDA_DATA = load_remote_json('miranda')
TIPS_DATA = load_remote_json('tips')
logger.info("Data loaded successfully")

DEFAULT_SETTINGS = {
    'opacity': 0.85,
    'is_minimized': False,
    'hotkey': 'f9',
    'window_x': 100,
    'window_y': 100,
    'window_width': 900,
    'window_height': 600,
    'click_through': False,
    'move_hotkey': 'f8'
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
        logger.error(f"Error loading settings: {e}")
    return DEFAULT_SETTINGS.copy()

def save_settings_to_file():
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(SETTINGS, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving settings: {e}")

def load_favorites():
    """Загружает избранные номера статей из файла"""
    try:
        if os.path.exists(FAVORITES_FILE):
            with open(FAVORITES_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Если favorites.json содержит список строк (номера статей)
                if isinstance(data, list):
                    return data
                # Если favorites.json содержит список объектов (старый формат)
                elif isinstance(data, dict) and 'articles' in data:
                    return data['articles']
                else:
                    return []
    except Exception as e:
        logger.error(f"Error loading favorites: {e}")
    return []

def save_favorites(favorites):
    """Сохраняет избранные номера статей в файл"""
    try:
        with open(FAVORITES_FILE, 'w', encoding='utf-8') as f:
            json.dump(favorites, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving favorites: {e}")
        return False

SETTINGS = load_settings()
FAVORITES = load_favorites()  # Теперь это список номеров статей (строки)

def find_free_port():
    for port in range(5000, 6000):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.1)
            if s.connect_ex(('127.0.0.1', port)) != 0:
                return port
    return 5000

PORT = find_free_port()
overlay_hwnd = None
is_moving_mode = False

def set_window_opacity(hwnd, opacity):
    try:
        alpha = int(opacity * 255)
        GWL_EXSTYLE = -20
        WS_EX_LAYERED = 0x80000
        LWA_ALPHA = 0x2
        
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style |= WS_EX_LAYERED
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        ctypes.windll.user32.SetLayeredWindowAttributes(hwnd, 0, alpha, LWA_ALPHA)
        return True
    except Exception as e:
        logger.error(f"Error setting opacity: {e}")
        return False

def set_click_through(hwnd, enabled):
    try:
        GWL_EXSTYLE = -20
        WS_EX_TRANSPARENT = 0x00000020
        WS_EX_LAYERED = 0x00080000
        WS_EX_NOACTIVATE = 0x08000000
        
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        
        if enabled:
            style |= WS_EX_TRANSPARENT
            style |= WS_EX_LAYERED
            style |= WS_EX_NOACTIVATE
        else:
            style &= ~WS_EX_TRANSPARENT
            style &= ~WS_EX_NOACTIVATE
        
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 
                                       0x0001 | 0x0002 | 0x0020)
        return True
    except Exception as e:
        logger.error(f"Error setting click-through: {e}")
        return False

def find_overlay_window():
    global overlay_hwnd
    
    if overlay_hwnd and win32gui.IsWindow(overlay_hwnd):
        return overlay_hwnd
    
    def enum_callback(hwnd, result):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if 'Законинск' in title or 'Россия Онлайн' in title:
                result.append(hwnd)
        return True
    
    windows = []
    win32gui.EnumWindows(enum_callback, windows)
    
    if windows:
        overlay_hwnd = windows[0]
        return overlay_hwnd
    
    return None

def apply_opacity_to_window():
    global overlay_hwnd
    hwnd = find_overlay_window()
    if hwnd:
        opacity = SETTINGS.get('opacity', 0.85)
        set_window_opacity(hwnd, opacity)
        return True
    return False

def apply_click_through_to_window():
    global overlay_hwnd, is_moving_mode
    hwnd = find_overlay_window()
    if hwnd:
        click_through = SETTINGS.get('click_through', False) and not is_moving_mode
        set_click_through(hwnd, click_through)
        return True
    return False

def extract_penalties(data):
    """Извлекает все статьи с наказаниями из структурированного JSON"""
    penalties = []
    
    def process_article(article, chapter_name):
        if not isinstance(article, dict):
            return
        
        # Проверяем наличие наказания или штрафов
        if 'наказание' in article or 'штрафы' in article:
            penalty_item = {
                'статья': f"Ст. {article.get('номер', '?')}",
                'номер_статьи': article.get('номер', '?'),
                'глава': chapter_name,
                'нарушение': article.get('текст', ''),
                'наказание': article.get('наказание', ''),
                'исключение': article.get('исключение', ''),
                'примечание': article.get('примечание', '')
            }
            
            # Обработка штрафов за скорость (статья 39)
            if 'штрафы' in article:
                penalty_item['детали'] = article['штрафы']
            
            # Обработка деталей
            if 'детали' in article and isinstance(article['детали'], list):
                penalty_item['детали'] = article['детали']
            
            penalties.append(penalty_item)
    
    # Проходим по всем главам
    if isinstance(data, dict) and 'главы' in data:
        for chapter in data['главы']:
            if isinstance(chapter, dict) and 'статьи' in chapter:
                chapter_name = chapter.get('название', '')
                for article in chapter['статьи']:
                    process_article(article, chapter_name)
    
    return penalties

def get_favorite_penalties():
    """Возвращает полные данные избранных статей по их номерам"""
    all_penalties = extract_penalties(LAW_DATA)
    favorite_penalties = []
    
    for penalty in all_penalties:
        article_number = penalty.get('номер_статьи', '')
        if article_number in FAVORITES:
            favorite_penalties.append(penalty)
    
    return favorite_penalties

@app.route('/')
def index():
    return render_template('index.html', app_version=APP_VERSION)

@app.route('/api/version')
def get_version():
    return jsonify({'version': APP_VERSION})

@app.route('/api/penalties')
def get_penalties():
    return jsonify(extract_penalties(LAW_DATA))

@app.route('/api/chapters')
def get_chapters():
    """Возвращает все главы"""
    if isinstance(LAW_DATA, dict) and 'главы' in LAW_DATA:
        return jsonify(LAW_DATA['главы'])
    return jsonify([])

@app.route('/api/search_penalties')
def search_penalties():
    query = request.args.get('q', '').lower()
    penalties = extract_penalties(LAW_DATA)
    if not query:
        return jsonify(penalties)
    return jsonify([p for p in penalties if query in json.dumps(p, ensure_ascii=False).lower()])

@app.route('/api/refresh_data', methods=['POST'])
def refresh_data():
    """Обновляет данные с сервера"""
    global LAW_DATA, MIRANDA_DATA, TIPS_DATA
    
    try:
        LAW_DATA = load_remote_json('DK')
        MIRANDA_DATA = load_remote_json('miranda')
        TIPS_DATA = load_remote_json('tips')
        return jsonify({'success': True, 'message': 'Данные обновлены'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/favorites', methods=['GET', 'POST', 'DELETE'])
def handle_favorites():
    global FAVORITES
    
    if request.method == 'GET':
        # Возвращаем полные данные избранных статей
        favorite_penalties = get_favorite_penalties()
        return jsonify(favorite_penalties)
    
    elif request.method == 'POST':
        data = request.json
        
        # Если пришел список номеров статей
        if data and isinstance(data, list):
            # Проверяем, что все элементы - строки (номера статей)
            if all(isinstance(item, str) for item in data):
                FAVORITES = data
                save_favorites(FAVORITES)
                return jsonify({'success': True, 'favorites': FAVORITES})
            # Если пришли объекты (старый формат), конвертируем
            else:
                FAVORITES = []
                for item in data:
                    if isinstance(item, dict) and 'номер_статьи' in item:
                        FAVORITES.append(item['номер_статьи'])
                    elif isinstance(item, dict) and 'статья' in item:
                        # Извлекаем номер из строки "Ст. 12"
                        article_str = item['статья']
                        if 'Ст. ' in article_str:
                            number = article_str.replace('Ст. ', '').strip()
                            FAVORITES.append(number)
                save_favorites(FAVORITES)
                return jsonify({'success': True, 'favorites': FAVORITES})
        
        # Если пришел объект с номером статьи
        elif data and isinstance(data, dict):
            article_number = data.get('номер_статьи') or data.get('статья', '')
            
            # Если передана строка "Ст. 12", извлекаем номер
            if isinstance(article_number, str) and 'Ст. ' in article_number:
                article_number = article_number.replace('Ст. ', '').strip()
            
            if article_number and article_number not in FAVORITES:
                FAVORITES.append(article_number)
                save_favorites(FAVORITES)
                return jsonify({'success': True, 'favorites': FAVORITES})
            return jsonify({'success': False, 'message': 'Already in favorites or invalid data'})
        
    elif request.method == 'DELETE':
        data = request.json
        if data:
            article_number = data.get('номер_статьи') or data.get('статья', '')
            
            # Если передана строка "Ст. 12", извлекаем номер
            if isinstance(article_number, str) and 'Ст. ' in article_number:
                article_number = article_number.replace('Ст. ', '').strip()
            
            if article_number in FAVORITES:
                FAVORITES.remove(article_number)
                save_favorites(FAVORITES)
                return jsonify({'success': True, 'favorites': FAVORITES})
    
    return jsonify({'success': False, 'message': 'Invalid request'})

@app.route('/api/miranda')
def get_miranda():
    return jsonify(MIRANDA_DATA)

@app.route('/api/tips')
def get_tips():
    return jsonify(TIPS_DATA)

@app.route('/api/settings', methods=['GET', 'POST'])
def handle_settings():
    global SETTINGS
    
    if request.method == 'POST':
        data = request.json
        if data:
            SETTINGS.update(data)
            save_settings_to_file()
            apply_opacity_to_window()
            apply_click_through_to_window()
            return jsonify({'success': True, 'settings': SETTINGS})
    
    return jsonify(SETTINGS)

@app.route('/api/toggle_click_through', methods=['POST'])
def toggle_click_through():
    global SETTINGS
    SETTINGS['click_through'] = not SETTINGS.get('click_through', False)
    save_settings_to_file()
    apply_click_through_to_window()
    return jsonify({'success': True, 'click_through': SETTINGS['click_through']})

@app.route('/api/toggle_moving_mode', methods=['POST'])
def toggle_moving_mode():
    global is_moving_mode
    is_moving_mode = not is_moving_mode
    apply_click_through_to_window()
    return jsonify({'success': True, 'moving_mode': is_moving_mode})

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

@app.route('/api/close_window')
def close_window():
    save_settings_to_file()
    save_favorites(FAVORITES)
    os._exit(0)
    return jsonify({'success': True})

class GTAOverlay:
    def __init__(self):
        self.window = None
        
    def start_flask(self):
        def run_flask():
            app.run(host='127.0.0.1', port=PORT, debug=False, use_reloader=False, threaded=True)
        
        self.flask_thread = threading.Thread(target=run_flask, daemon=True)
        self.flask_thread.start()
    
    def create_window(self, loading_window=None):
        if loading_window:
            loading_window.update_status("Запуск сервера...")
        
        self.start_flask()
        time.sleep(2)
        
        if loading_window:
            loading_window.update_status("Создание окна...")
        
        url = f'http://127.0.0.1:{PORT}'
        
        if loading_window:
            loading_window.close()
        
        self.window = webview.create_window(
            'Законинск - Россия Онлайн',
            url,
            width=900,
            height=600,
            x=SETTINGS.get('window_x', 100),
            y=SETTINGS.get('window_y', 100),
            resizable=True,
            frameless=True,
            on_top=True,
            transparent=False,
            background_color='#1a1a1a',
            easy_drag=True
        )
        
        webview.start(self.on_webview_started, debug=False)
    
    def on_webview_started(self):
        logger.info("WebView started")
        time.sleep(2)
        apply_opacity_to_window()
        apply_click_through_to_window()
        
        def opacity_loop():
            while True:
                time.sleep(3)
                apply_opacity_to_window()
        
        threading.Thread(target=opacity_loop, daemon=True).start()
        
        def hotkey_loop():
            try:
                keyboard.add_hotkey(SETTINGS.get('hotkey', 'f9'), self.toggle_minimize)
                keyboard.add_hotkey('f10', self.toggle_click_through_mode)
                keyboard.add_hotkey(SETTINGS.get('move_hotkey', 'f8'), self.toggle_moving_mode)
            except:
                pass
            while True:
                time.sleep(1)
        
        threading.Thread(target=hotkey_loop, daemon=True).start()
    
    def toggle_click_through_mode(self):
        global is_moving_mode
        is_moving_mode = False
        SETTINGS['click_through'] = not SETTINGS.get('click_through', False)
        save_settings_to_file()
        apply_click_through_to_window()
        
        try:
            if self.window:
                state = "включен" if SETTINGS['click_through'] else "выключен"
                self.window.evaluate_js(f'showNotification("Click-through {state}")')
        except:
            pass
    
    def toggle_moving_mode(self):
        global is_moving_mode
        is_moving_mode = not is_moving_mode
        apply_click_through_to_window()
        
        try:
            if self.window:
                state = "включен" if is_moving_mode else "выключен"
                self.window.evaluate_js(f'showNotification("Режим перемещения {state}")')
        except:
            pass
    
    def toggle_minimize(self):
        if SETTINGS.get('is_minimized', False):
            SETTINGS['is_minimized'] = False
        else:
            SETTINGS['is_minimized'] = True
        
        try:
            if self.window:
                self.window.evaluate_js(f'toggleMinimizedState({str(SETTINGS["is_minimized"]).lower()})')
        except:
            pass

def main():
    loading = LoadingWindow()
    loading.update_status("Загрузка данных...")
    
    overlay = GTAOverlay()
    overlay.create_window(loading)

if __name__ == '__main__':
    main()