import json
import threading
import webview
from flask import Flask, render_template, request, jsonify
import win32gui
import win32con
import win32process
import psutil
import time
import ctypes
import win32api
import keyboard
import os
import sys
import logging
import socket
import tkinter as tk
from tkinter import ttk

# Константы в начале
APP_VERSION = '24.08.26#002-STABLE'

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
        
        # Красная полоска сверху
        top_bar = tk.Frame(self.root, bg='#cc0000', height=3)
        top_bar.pack(side='top', fill='x')
        
        # Заголовок
        title_frame = tk.Frame(self.root, bg='#1a1a1a')
        title_frame.pack(fill='x', pady=(15, 5))
        
        title_label = tk.Label(
            title_frame, 
            text="📋 Законинск", 
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
        
        # Статус загрузки
        self.status_label = tk.Label(
            self.root,
            text="Запуск...",
            font=('Segoe UI', 11),
            fg='#ff4444',
            bg='#1a1a1a'
        )
        self.status_label.pack(pady=(5, 5))
        
        # Прогресс-бар
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
        
        # Копирайт
        copyright_label = tk.Label(
            self.root,
            text="media by: EG | created by: prostochel096",
            font=('Segoe UI', 8),
            fg='#555555',
            bg='#1a1a1a'
        )
        copyright_label.pack(side='bottom', pady=5)
    
    def update_status(self, text):
        """Обновляет текст статуса"""
        try:
            if self.root and self.root.winfo_exists():
                self.status_label.config(text=text)
                self.root.update_idletasks()
                self.root.update()
        except:
            pass
    
    def close(self):
        """Закрывает окно загрузки"""
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

if getattr(sys, 'frozen', False):
    SETTINGS_FILE = os.path.join(os.path.dirname(sys.executable), 'settings.json')
    DATA_FILE = os.path.join(BASE_DIR, 'data.json')
else:
    SETTINGS_FILE = os.path.join(BASE_DIR, 'settings.json')
    DATA_FILE = os.path.join(BASE_DIR, 'data.json')

try:
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        LAW_DATA = json.load(f)
except Exception as e:
    logger.error(f"Error loading data: {e}")
    LAW_DATA = {}

DEFAULT_SETTINGS = {
    'opacity': 0.85,
    'is_minimized': False,
    'hotkey': 'f9',
    'window_x': 100,
    'window_y': 100,
    'window_width': 500,
    'window_height': 600,
    'click_through': True,  # По умолчанию включено для игры
    'game_process_name': 'GTA5.exe',  # Имя процесса игры
    'move_hotkey': 'f8'  # Горячая клавиша для перемещения
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

SETTINGS = load_settings()

def find_free_port():
    for port in range(5000, 6000):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.1)
            if s.connect_ex(('127.0.0.1', port)) != 0:
                return port
    return 5000

PORT = find_free_port()
overlay_hwnd = None
is_moving_mode = False  # Режим перемещения окна

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
    """Включает или выключает click-through для окна"""
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
        
        # Обновляем окно
        ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 
                                       0x0001 | 0x0002 | 0x0020)  # SWP_NOMOVE | SWP_NOSIZE | SWP_FRAMECHANGED
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
    """Применяет настройку click-through к окну"""
    global overlay_hwnd, is_moving_mode
    
    hwnd = find_overlay_window()
    if hwnd:
        # Если режим перемещения включен, отключаем click-through
        click_through = SETTINGS.get('click_through', True) and not is_moving_mode
        set_click_through(hwnd, click_through)
        return True
    return False

def is_game_running():
    """Проверяет, запущен ли процесс игры"""
    try:
        game_process_name = SETTINGS.get('game_process_name', 'GTA5.exe')
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] and proc.info['name'].lower() == game_process_name.lower():
                return True
        return False
    except:
        return False

def is_game_active():
    """Проверяет, активно ли окно игры"""
    try:
        hwnd = win32gui.GetForegroundWindow()
        if hwnd:
            # Получаем PID процесса окна
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                process = psutil.Process(pid)
                process_name = process.name()
                
                # Проверяем, является ли активное окно игрой
                game_process_name = SETTINGS.get('game_process_name', 'GTA5.exe')
                if process_name.lower() == game_process_name.lower():
                    return True
            except:
                pass
            
            # Также проверяем заголовок окна
            title = win32gui.GetWindowText(hwnd)
            if any(keyword in title.lower() for keyword in ['gta', 'grand theft auto', 'rockstar']):
                return True
    except:
        pass
    return False

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
        elif isinstance(obj, dict):
            for key, value in obj.items():
                if key == 'заголовок':
                    section_name = value
                recursive_extract(value, section_name)
    
    recursive_extract(data)
    
    unique = []
    seen = set()
    for p in penalties:
        key = json.dumps(p, ensure_ascii=False)
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique

@app.route('/')
def index():
    return render_template('index.html', app_version=APP_VERSION)

@app.route('/api/version')
def get_version():
    return jsonify({'version': APP_VERSION})

@app.route('/api/penalties')
def get_penalties():
    return jsonify(extract_penalties(LAW_DATA))

@app.route('/api/search_penalties')
def search_penalties():
    query = request.args.get('q', '').lower()
    penalties = extract_penalties(LAW_DATA)
    if not query:
        return jsonify(penalties)
    return jsonify([p for p in penalties if query in json.dumps(p, ensure_ascii=False).lower()])

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
    """Переключает режим click-through"""
    global SETTINGS
    SETTINGS['click_through'] = not SETTINGS.get('click_through', False)
    save_settings_to_file()
    apply_click_through_to_window()
    return jsonify({'success': True, 'click_through': SETTINGS['click_through']})

@app.route('/api/toggle_moving_mode', methods=['POST'])
def toggle_moving_mode():
    """Переключает режим перемещения окна"""
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
    os._exit(0)
    return jsonify({'success': True})

class GTAOverlay:
    def __init__(self):
        self.window = None
        self.is_game_was_active = False
        
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
        
        # Закрываем окно загрузки
        if loading_window:
            loading_window.close()
        
        self.window = webview.create_window(
            'Законинск - Россия Онлайн',
            url,
            width=600,
            height=500,
            x=SETTINGS.get('window_x', 100),
            y=SETTINGS.get('window_y', 100),
            resizable=True,
            frameless=True,
            on_top=True,
            transparent=False,
            background_color='#1a1a1a',
            easy_drag=True  # Включаем easy_drag
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
        
        # Запускаем мониторинг состояния игры
        def game_monitor_loop():
            while True:
                time.sleep(0.3)  # Проверяем каждые 0.3 секунды
                self.check_game_state()
        
        threading.Thread(target=game_monitor_loop, daemon=True).start()
    
    def check_game_state(self):
        """Проверяет состояние игры и автоматически переключает click-through"""
        global is_moving_mode
        try:
            game_active = is_game_active()
            
            # Если режим перемещения включен, не меняем click-through автоматически
            if is_moving_mode:
                return
            
            # Если состояние изменилось
            if game_active != self.is_game_was_active:
                if game_active:
                    # Игра стала активной - включаем click-through
                    SETTINGS['click_through'] = True
                    save_settings_to_file()
                    apply_click_through_to_window()
                    logger.info("Game activated, enabling click-through")
                    
                    # Уведомляем интерфейс
                    try:
                        if self.window:
                            self.window.evaluate_js('showNotification("Режим игры: клики проходят сквозь окно")')
                    except:
                        pass
                else:
                    # Игра стала неактивной - выключаем click-through
                    SETTINGS['click_through'] = False
                    save_settings_to_file()
                    apply_click_through_to_window()
                    logger.info("Game deactivated, disabling click-through")
                    
                    # Уведомляем интерфейс
                    try:
                        if self.window:
                            self.window.evaluate_js('showNotification("Режим рабочего стола: окно активно")')
                    except:
                        pass
                
                self.is_game_was_active = game_active
                
        except Exception as e:
            logger.error(f"Error in game state check: {e}")
    
    def toggle_click_through_mode(self):
        """Ручное переключение click-through режима"""
        global is_moving_mode
        is_moving_mode = False  # Выключаем режим перемещения
        SETTINGS['click_through'] = not SETTINGS.get('click_through', False)
        save_settings_to_file()
        apply_click_through_to_window()
        
        # Показываем уведомление в окне
        try:
            if self.window:
                state = "включен" if SETTINGS['click_through'] else "выключен"
                self.window.evaluate_js(f'showNotification("Click-through {state}")')
        except:
            pass
    
    def toggle_moving_mode(self):
        """Переключает режим перемещения окна"""
        global is_moving_mode
        is_moving_mode = not is_moving_mode
        apply_click_through_to_window()
        
        # Показываем уведомление в окне
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
    """Основная функция"""
    # Создаем окно загрузки
    loading = LoadingWindow()
    loading.update_status("Инициализация...")
    
    # Запускаем приложение
    overlay = GTAOverlay()
    overlay.create_window(loading)

if __name__ == '__main__':
    main()