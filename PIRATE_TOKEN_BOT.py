import ctypes, json, math, os, random, sys, time, threading, traceback, webbrowser, tkinter as tk
from tkinter import messagebox

APP_DIR = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(APP_DIR, "error.log")
TELEGRAM_URL = "https://t.me/outmoneyfortnite"


def log_error(text):
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + text + "\n")
    except Exception:
        pass


try:  # чтобы координаты совпадали при масштабе Windows 125%/150%
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

try:  # своя иконка в панели задач (а не иконка Python)
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("outmoney.PirateTokenBot")
except Exception:
    pass

try:
    import pyautogui, keyboard
    from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageGrab, ImageStat, ImageTk
except Exception:
    err = traceback.format_exc()
    log_error(err)
    _r = tk.Tk()
    _r.withdraw()
    messagebox.showerror("PIRATE TOKEN BOT",
                         "Не хватает модулей. Выполните в cmd:\n\npy -m pip install pyautogui keyboard pillow\n\n" + err)
    sys.exit(1)

pyautogui.FAILSAFE = True   # мышь в левый верхний угол = аварийная остановка
pyautogui.PAUSE = 0.05

# Звуки переключения Start/Stop. WAV поддерживается Windows без дополнительных библиотек.
try:
    import winsound
except Exception:
    winsound = None


def asset_path(filename):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, filename)


def _play(sound_name):
    if winsound is None or not cfg.get("sound_enabled", True):
        return
    try:
        winsound.PlaySound(asset_path(sound_name + ".wav"),
                           winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
    except Exception:
        log_error("Could not play sound:\n" + traceback.format_exc())


def play_toggle_sound():
    """Звук запуска (выбранный в Interface)."""
    sound_name = cfg.get("sound", "Sound 1")
    if sound_name in [f"Sound {i}" for i in range(1, 10)]:
        _play(sound_name)


def play_stop_sound():
    """Звук отключения."""
    _play("Sound Stop")


quitting = False   # при закрытии программы звук остановки не играем


CFG_PATH = os.path.join(APP_DIR, "bot_config.json")
DEFAULTS = {
    "match_min": 1,          # длительность матча (минуты), считается от клика по Play
    "lobby_sec": 15,         # ожидание лобби после выхода (секунды)
    "hotkey": "F8",
    "theme": "Purple",
    "language": "English",
    "sound": "Sound 1",
    "sound_enabled": True,
    "play":    [313, 892],
    "leave":   [1696, 74],   # три полоски справа сверху
    "confirm": [1603, 187],  # крестик «Выход с матча»
    "rmb":     [100, 980],   # ПКМ в левой нижней части экрана
    # --- Антибан: случайные одновременные действия во время матча ---
    "ab_enabled": False,
    "ab_keys": {"w": True, "a": True, "s": True, "d": True, "shift": True, "space": True, "lmb": True,
                "mouse": True, "custom": False},
    "ab_custom_key": "r",    # своя клавиша антибана (меняется в разделе «Антибан»)
    "ab_pmin": 0.3,          # минимальная пауза между действиями (сек)
    "ab_pmax": 2.0,          # максимальная пауза (сек)
    "ab_amax": 2.5,          # максимальная длительность одного действия (сек)
    "ab_delay": 30,          # через сколько секунд после клика по Play начинать (сек)
    "ab_pixel_on": False,    # действовать только если «маркер матча» на экране совпадает по цвету
    "ab_pixel": None,        # [x, y, "#rrggbb"] — маркер матча (ставится клавишей F11)
    # --- Контроль команды: выход из матча, когда погибли все 4 игрока ---
    "auto_skip_survey": True,   # сам нажимать «Пропустить» на экране опроса
    "td_enabled": False,
    "td_slots": [None, None, None, None],   # по игроку: [x, y, "#rrggbb"] — явный признак смерти
    "td_popup": None,                       # [x, y, "#rrggbb"] — кнопка окна преждевременного запуска новой катки
}

cfg = json.loads(json.dumps(DEFAULTS))
if os.path.exists(CFG_PATH):
    try:
        cfg.update(json.load(open(CFG_PATH, encoding="utf-8")))
    except Exception:
        pass

if not isinstance(cfg.get("td_slots"), list) or len(cfg["td_slots"]) != 4:
    cfg["td_slots"] = [None, None, None, None]
cfg["ab_keys"] = {**DEFAULTS["ab_keys"], **(cfg.get("ab_keys") if isinstance(cfg.get("ab_keys"), dict) else {})}

FONT = "Segoe UI"

# ---------------- темы ----------------
THEMES = {
    "Purple": {
        "BG": "#0f111a", "SIDE": "#0b0d14", "CARD": "#151824", "FIELD": "#0b0d14",
        "ACC": "#6c47ff", "ACC_H": "#7d5cff", "TXT": "#ffffff", "MUT": "#8b90a3",
        "RED": "#ff4d6d", "RED_H": "#ff6b85", "GREEN": "#3ddc84", "LINE": "#23283a",
        "BTN": "#1a1e2e", "HOVER": "#2a3048",
    },
    "Black": {
        "BG": "#090909", "SIDE": "#050505", "CARD": "#151515", "FIELD": "#080808",
        "ACC": "#555555", "ACC_H": "#8a8a8a", "TXT": "#f5f5f5", "MUT": "#a0a0a0",
        "RED": "#e04b5a", "RED_H": "#ee6a77", "GREEN": "#55c98a", "LINE": "#303030",
        "BTN": "#242424", "HOVER": "#363636",
    },
    "White": {
        "BG": "#f1f2f4", "SIDE": "#e5e7eb", "CARD": "#ffffff", "FIELD": "#f7f8fa",
        "ACC": "#6b7280", "ACC_H": "#4b5563", "TXT": "#20242b", "MUT": "#68707c",
        "RED": "#cf465b", "RED_H": "#dd6074", "GREEN": "#25845a", "LINE": "#d5d9df",
        "BTN": "#e7e9ed", "HOVER": "#d3d7de",
    },
}
ACT_FG = "#ffffff"   # текст на акцентном фоне (активный пункт, кнопка)
if cfg.get("sound") not in [f"Sound {i}" for i in range(1, 10)]:
    cfg["sound"] = "Sound 1"
if cfg.get("theme") not in THEMES:
    cfg["theme"] = "Purple"
P = dict(THEMES[cfg["theme"]])   # текущая палитра

# Все виджеты, которые зависят от темы: (виджет, {опция: имя_цвета_палитры})
_themed = []


def _col(role):
    return role if role.startswith("#") else P[role]


def TH(widget, **roles):
    _themed.append((widget, roles))
    try:
        widget.configure(**{opt: _col(role) for opt, role in roles.items()})
    except tk.TclError:
        pass
    return widget


# ---------------- переводы ----------------
LANGS = ["English", "Русский", "Українська", "Қазақша"]
if cfg.get("language") not in LANGS:
    cfg["language"] = "English"

EN = {
    "nav_overview": "CONTROL CENTER", "nav_settings": "SETTINGS", "nav_interface": "INTERFACE",
    "cc_title": "Control Center", "cc_sub": "Manage your queue cycle and monitor the current session.",
    "sys_status": "SYSTEM STATUS", "next_cycle": "NEXT CYCLE", "match_duration": "MATCH DURATION",
    "lobby_delay": "LOBBY DELAY", "completed": "COMPLETED ROUNDS",
    "start_queue": "▶   START QUEUE", "stop_queue": "■   STOP QUEUE",
    "hint": "{0} START / STOP   •   F9 COPY MOUSE POSITION   •   F10 EXIT",
    "settings_title": "Settings", "settings_sub": "Adjust the cycle timing and in-game button coordinates.",
    "timing": "TIMING", "match_min_lbl": "Match duration (minutes)", "lobby_sec_lbl": "Lobby delay (seconds)",
    "hotkey_lbl": "Start / Stop key", "change": "CHANGE", "press_key": "PRESS ANY KEY…",
    "coords": "BUTTON COORDINATES", "play": "Play", "leave": "Leave", "confirm": "Confirm",
    "rclick": "Right click", "save": "SAVE SETTINGS", "reset": "RESET DEFAULTS",
    "ui_title": "Interface", "ui_sub": "Choose the application theme and language.",
    "appearance": "APPEARANCE", "theme": "Theme", "language": "Language",
    "sound_lbl": "Start sound", "sound_n": "Sound {0}", "sound_on": "Enable sound",
    "theme_Purple": "Purple", "theme_Black": "Black", "theme_White": "White",
    "ph_stopped": "STOPPED", "ph_match": "IN MATCH", "ph_leaving": "LEAVING", "ph_lobby": "LOBBY",
    "sub_ready": "Ready when you are. Start the queue to begin.",
    "sub_match": "Waiting for the match timer to finish.", "sub_leaving": "Leaving the match...",
    "sub_lobby": "Waiting for the lobby.",
    "sub_failsafe": "Stopped: mouse was in the top-left corner (fail-safe).", "sub_error": "Error: {0}",
    "note_default": "Changes apply to the next queue cycle.", "note_saved": "Settings saved.",
    "note_defaults": "Defaults restored.", "note_numbers": "Error: all fields must be numbers.",
    "note_hotkey": "Hotkey selected: {0}", "note_copied": "Copied mouse position: {0}, {1}",
    "note_hk_err": "Hotkey error: {0} (run as administrator)", "note_cap_err": "Could not capture key: {0}",
    "ab_pmin_lbl": "Pause from (s)", "ab_pmax_lbl": "Pause to (s)", "ab_amax_lbl": "Action up to (s)", "ab_pixel_on": "Act only in a match", "ab_marker_hint": "Marker: hover over something visible only in a match (e.g. the health bar) and press F11.", "marker_none": "not set", "note_marker": "Match marker set: {0}, {1}  {2}", "note_marker_err": "Could not read the marker: {0}", "key_mouse": "Mouse movement", "nav_team": "TEAM WATCH", "td_title": "Team Watch", "td_sub": "The match ends early only when all 4 players, including you, are confirmed dead 3 checks in a row.", "td_enable": "Leave the match when the whole team is dead", "td_signs": "DEATH SIGN OF EACH PLAYER", "td_player": "Player {0}", "td_popup": "Popup (never click)", "td_set": "SET", "td_clear": "CLEAR ALL", "td_hint": "Press SET, then within 4 seconds point the cursor at the clear visual death sign of that player in the game. Popup: point at the button that starts a new match too early.", "td_state_off": "Check is off. The match ends by the timer only.", "td_state_incomplete": "Set all 4 death signs, otherwise the check stays off ({0}/4 set).", "td_state_ready": "Ready: the match ends when all 4 are dead 3 checks in a row.", "td_wait": "Point the cursor at: {0}   {1}", "td_slot_set": "{0} saved: {1}, {2}  {3}", "sub_team_dead": "All 4 players are dead. Leaving the match...", "survey_auto": "Auto-skip the survey screen (Skip button)", "note_survey_skipped": "Survey screen detected: Skip pressed.", "nav_antiban": "ANTI-BAN", "ab_title": "Anti-ban",
    "ab_sub": "Random simultaneous actions during the match: walking, sprint, jump, clicks and mouse movement.",
    "ab_enable": "Enable anti-ban", "ab_keys": "KEYS TO PRESS",
    "key_w": "W", "key_a": "A", "key_s": "S", "key_d": "D", "key_shift": "Shift",
    "key_space": "Space", "key_lmb": "Left mouse button", "key_custom": "Custom key",
    "note_custom_key": "Custom key selected: {0}",
    "ab_timing": "ACTION TIMING", "ab_delay_lbl": "Start after Play (s)", "ab_save": "SAVE ANTI-BAN",
    "note_ab_saved": "Anti-ban settings saved.", "note_ab_range": "Error: min pause cannot be greater than max.",
    "version": "Version 1.4", "tg_channel": "Telegram Channel",
}

TR = {
    "Русский": {
        "nav_overview": "ЦЕНТР УПРАВЛЕНИЯ", "nav_settings": "НАСТРОЙКИ", "nav_interface": "ИНТЕРФЕЙС",
        "cc_title": "Центр управления", "cc_sub": "Управление циклом и текущей сессией.",
        "sys_status": "СОСТОЯНИЕ СИСТЕМЫ", "next_cycle": "СЛЕДУЮЩИЙ ЦИКЛ", "match_duration": "ДЛИТЕЛЬНОСТЬ МАТЧА",
        "lobby_delay": "ОЖИДАНИЕ ЛОББИ", "completed": "ЗАВЕРШЁННЫЕ ЦИКЛЫ",
        "start_queue": "▶   ЗАПУСТИТЬ ОЧЕРЕДЬ", "stop_queue": "■   ОСТАНОВИТЬ ОЧЕРЕДЬ",
        "hint": "{0} СТАРТ / СТОП   •   F9 КОПИРОВАТЬ КООРДИНАТЫ МЫШИ   •   F10 ВЫХОД",
        "settings_title": "Настройки", "settings_sub": "Настройка времени цикла и координат кнопок.",
        "timing": "ТАЙМИНГ", "match_min_lbl": "Длительность матча (минуты)", "lobby_sec_lbl": "Ожидание лобби (секунды)",
        "hotkey_lbl": "Клавиша Старт / Стоп", "change": "СМЕНИТЬ", "press_key": "НАЖМИТЕ ЛЮБУЮ КЛАВИШУ…",
        "coords": "КООРДИНАТЫ КНОПОК", "play": "Играть", "leave": "Выйти", "confirm": "Подтвердить",
        "rclick": "Правая кнопка мыши", "save": "СОХРАНИТЬ", "reset": "СБРОСИТЬ",
        "ui_title": "Интерфейс", "ui_sub": "Выберите тему и язык приложения.",
        "appearance": "ВНЕШНИЙ ВИД", "theme": "Тема", "language": "Язык",
        "sound_lbl": "Звук запуска", "sound_n": "Звук {0}", "sound_on": "Включить звук",
        "theme_Purple": "Фиолетовая", "theme_Black": "Чёрная", "theme_White": "Белая",
        "ph_stopped": "ОСТАНОВЛЕНО", "ph_match": "В МАТЧЕ", "ph_leaving": "ВЫХОД", "ph_lobby": "ЛОББИ",
        "sub_ready": "Готово. Нажмите запуск, чтобы начать.",
        "sub_match": "Ожидание окончания таймера матча.", "sub_leaving": "Выход из матча...",
        "sub_lobby": "Ожидание лобби.",
        "sub_failsafe": "Остановлено: мышь в левом верхнем углу (аварийная остановка).", "sub_error": "Ошибка: {0}",
        "note_default": "Изменения применяются со следующего цикла.", "note_saved": "Настройки сохранены.",
        "note_defaults": "Настройки сброшены.", "note_numbers": "Ошибка: все поля должны быть числами.",
        "note_hotkey": "Выбрана клавиша: {0}", "note_copied": "Координаты мыши скопированы: {0}, {1}",
        "note_hk_err": "Ошибка горячей клавиши: {0} (запустите от администратора)",
        "note_cap_err": "Не удалось считать клавишу: {0}",
        "ab_pmin_lbl": "Пауза от (с)", "ab_pmax_lbl": "Пауза до (с)", "ab_amax_lbl": "Действие до (с)", "ab_pixel_on": "Только в матче", "ab_marker_hint": "Маркер: наведи курсор на то, что видно только в матче (например, полоску здоровья), и нажми F11.", "marker_none": "не задан", "note_marker": "Маркер матча задан: {0}, {1}  {2}", "note_marker_err": "Не удалось прочитать маркер: {0}", "key_mouse": "Движение мыши", "nav_team": "КОНТРОЛЬ КОМАНДЫ", "td_title": "Контроль команды", "td_sub": "Катка завершается досрочно, только если все 4 игрока, включая тебя, подтверждённо погибли 3 проверки подряд.", "td_enable": "Выходить из матча, когда погибла вся команда", "td_signs": "ПРИЗНАК СМЕРТИ КАЖДОГО ИГРОКА", "td_player": "Игрок {0}", "td_popup": "Окно запуска (не нажимать)", "td_set": "ЗАДАТЬ", "td_clear": "ОЧИСТИТЬ", "td_hint": "Нажми «Задать», затем в течение 4 секунд наведи курсор на явный визуальный признак смерти этого игрока в игре. Для окна запуска — на кнопку, которая преждевременно запускает новую катку.", "td_state_off": "Проверка выключена. Катка заканчивается только по таймеру.", "td_state_incomplete": "Задай признаки всех 4 игроков, иначе проверка не работает (задано {0}/4).", "td_state_ready": "Готово: катка завершится, когда все 4 погибли 3 проверки подряд.", "td_wait": "Наведи курсор на: {0}   {1}", "td_slot_set": "{0} сохранён: {1}, {2}  {3}", "sub_team_dead": "Все 4 игрока погибли. Выход из матча...", "survey_auto": "Авто-пропуск экрана опроса (кнопка «Пропустить»)", "note_survey_skipped": "Найден экран опроса: нажато «Пропустить».", "nav_antiban": "АНТИБАН", "ab_title": "Антибан",
        "ab_sub": "Случайные одновременные действия во время матча: ходьба, бег, прыжок, клики и движение мыши.",
        "ab_enable": "Включить антибан", "ab_keys": "НАЖИМАЕМЫЕ КЛАВИШИ",
        "key_w": "W", "key_a": "A", "key_s": "S", "key_d": "D", "key_shift": "Shift",
        "key_space": "Пробел", "key_lmb": "Левая кнопка мыши (ЛКМ)", "key_custom": "Своя клавиша",
        "note_custom_key": "Выбрана своя клавиша: {0}",
        "ab_timing": "ТАЙМИНГ ДЕЙСТВИЙ", "ab_delay_lbl": "Старт после Play (с)", "ab_save": "СОХРАНИТЬ АНТИБАН",
        "note_ab_saved": "Настройки антибана сохранены.", "note_ab_range": "Ошибка: мин. пауза не может быть больше макс.",
        "version": "Версия 1.4", "tg_channel": "Telegram-канал",
    },
    "Українська": {
        "nav_overview": "ЦЕНТР КЕРУВАННЯ", "nav_settings": "НАЛАШТУВАННЯ", "nav_interface": "ІНТЕРФЕЙС",
        "cc_title": "Центр керування", "cc_sub": "Керування циклом і поточною сесією.",
        "sys_status": "СТАН СИСТЕМИ", "next_cycle": "НАСТУПНИЙ ЦИКЛ", "match_duration": "ТРИВАЛІСТЬ МАТЧУ",
        "lobby_delay": "ОЧІКУВАННЯ ЛОБІ", "completed": "ЗАВЕРШЕНІ ЦИКЛИ",
        "start_queue": "▶   ЗАПУСТИТИ ЧЕРГУ", "stop_queue": "■   ЗУПИНИТИ ЧЕРГУ",
        "hint": "{0} СТАРТ / СТОП   •   F9 КОПІЮВАТИ КООРДИНАТИ МИШІ   •   F10 ВИХІД",
        "settings_title": "Налаштування", "settings_sub": "Налаштування часу циклу та координат кнопок.",
        "timing": "ТАЙМІНГ", "match_min_lbl": "Тривалість матчу (хвилини)", "lobby_sec_lbl": "Очікування лобі (секунди)",
        "hotkey_lbl": "Клавіша Старт / Стоп", "change": "ЗМІНИТИ", "press_key": "НАТИСНІТЬ БУДЬ-ЯКУ КЛАВІШУ…",
        "coords": "КООРДИНАТИ КНОПОК", "play": "Грати", "leave": "Вийти", "confirm": "Підтвердити",
        "rclick": "Права кнопка миші", "save": "ЗБЕРЕГТИ", "reset": "СКИНУТИ",
        "ui_title": "Інтерфейс", "ui_sub": "Оберіть тему та мову застосунку.",
        "appearance": "ВИГЛЯД", "theme": "Тема", "language": "Мова",
        "sound_lbl": "Звук запуску", "sound_n": "Звук {0}", "sound_on": "Увімкнути звук",
        "theme_Purple": "Фіолетова", "theme_Black": "Чорна", "theme_White": "Біла",
        "ph_stopped": "ЗУПИНЕНО", "ph_match": "У МАТЧІ", "ph_leaving": "ВИХІД", "ph_lobby": "ЛОБІ",
        "sub_ready": "Готово. Натисніть запуск, щоб почати.",
        "sub_match": "Очікування завершення таймера матчу.", "sub_leaving": "Вихід із матчу...",
        "sub_lobby": "Очікування лобі.",
        "sub_failsafe": "Зупинено: миша в лівому верхньому куті (аварійна зупинка).", "sub_error": "Помилка: {0}",
        "note_default": "Зміни застосовуються з наступного циклу.", "note_saved": "Налаштування збережено.",
        "note_defaults": "Налаштування скинуто.", "note_numbers": "Помилка: усі поля мають бути числами.",
        "note_hotkey": "Обрано клавішу: {0}", "note_copied": "Координати миші скопійовано: {0}, {1}",
        "note_hk_err": "Помилка гарячої клавіші: {0} (запустіть від адміністратора)",
        "note_cap_err": "Не вдалося зчитати клавішу: {0}",
        "ab_pmin_lbl": "Пауза від (с)", "ab_pmax_lbl": "Пауза до (с)", "ab_amax_lbl": "Дія до (с)", "ab_pixel_on": "Лише в матчі", "ab_marker_hint": "Маркер: наведіть курсор на те, що видно лише в матчі (наприклад, смужку здоров'я), і натисніть F11.", "marker_none": "не задано", "note_marker": "Маркер матчу задано: {0}, {1}  {2}", "note_marker_err": "Не вдалося прочитати маркер: {0}", "key_mouse": "Рух миші", "nav_team": "КОНТРОЛЬ КОМАНДИ", "td_title": "Контроль команди", "td_sub": "Катка завершується достроково, лише якщо всі 4 гравці, включно з тобою, підтверджено загинули 3 перевірки поспіль.", "td_enable": "Виходити з матчу, коли загинула вся команда", "td_signs": "ОЗНАКА СМЕРТІ КОЖНОГО ГРАВЦЯ", "td_player": "Гравець {0}", "td_popup": "Вікно запуску (не натискати)", "td_set": "ЗАДАТИ", "td_clear": "ОЧИСТИТИ", "td_hint": "Натисни «Задати», потім протягом 4 секунд наведи курсор на явну візуальну ознаку смерті цього гравця в грі. Для вікна запуску — на кнопку, яка передчасно запускає нову катку.", "td_state_off": "Перевірку вимкнено. Катка закінчується лише за таймером.", "td_state_incomplete": "Задай ознаки всіх 4 гравців, інакше перевірка не працює (задано {0}/4).", "td_state_ready": "Готово: катка завершиться, коли всі 4 загинули 3 перевірки поспіль.", "td_wait": "Наведи курсор на: {0}   {1}", "td_slot_set": "{0} збережено: {1}, {2}  {3}", "sub_team_dead": "Усі 4 гравці загинули. Вихід із матчу...", "survey_auto": "Авто-пропуск екрана опитування (кнопка «Пропустити»)", "note_survey_skipped": "Знайдено екран опитування: натиснуто «Пропустити».", "nav_antiban": "АНТИБАН", "ab_title": "Антибан",
        "ab_sub": "Випадкові одночасні дії під час матчу: ходьба, біг, стрибок, кліки та рух миші.",
        "ab_enable": "Увімкнути антибан", "ab_keys": "КЛАВІШІ ДЛЯ НАТИСКАННЯ",
        "key_w": "W", "key_a": "A", "key_s": "S", "key_d": "D", "key_shift": "Shift",
        "key_space": "Пробіл", "key_lmb": "Ліва кнопка миші (ЛКМ)", "key_custom": "Власна клавіша",
        "note_custom_key": "Обрано власну клавішу: {0}",
        "ab_timing": "ТАЙМІНГ ДІЙ", "ab_delay_lbl": "Старт після Play (с)", "ab_save": "ЗБЕРЕГТИ АНТИБАН",
        "note_ab_saved": "Налаштування антибану збережено.", "note_ab_range": "Помилка: мін. пауза не може бути більшою за макс.",
        "version": "Версія 1.4", "tg_channel": "Telegram-канал",
    },
    "Қазақша": {
        "nav_overview": "БАСҚАРУ ОРТАЛЫҒЫ", "nav_settings": "БАПТАУЛАР", "nav_interface": "ИНТЕРФЕЙС",
        "cc_title": "Басқару орталығы", "cc_sub": "Кезек циклін және ағымдағы сеансты басқару.",
        "sys_status": "ЖҮЙЕ КҮЙІ", "next_cycle": "КЕЛЕСІ ЦИКЛ", "match_duration": "МАТЧ ҰЗАҚТЫҒЫ",
        "lobby_delay": "ЛОББИДЕ КҮТУ", "completed": "АЯҚТАЛҒАН ЦИКЛДЕР",
        "start_queue": "▶   КЕЗЕКТІ БАСТАУ", "stop_queue": "■   КЕЗЕКТІ ТОҚТАТУ",
        "hint": "{0} БАСТАУ / ТОҚТАТУ   •   F9 ТІНТУІР КООРДИНАТТАРЫН КӨШІРУ   •   F10 ШЫҒУ",
        "settings_title": "Баптаулар", "settings_sub": "Цикл уақытын және ойын ішіндегі батырма координаттарын баптау.",
        "timing": "УАҚЫТ", "match_min_lbl": "Матч ұзақтығы (минут)", "lobby_sec_lbl": "Лоббиде күту (секунд)",
        "hotkey_lbl": "Бастау / тоқтату пернесі", "change": "ӨЗГЕРТУ", "press_key": "КЕЗ КЕЛГЕН ПЕРНЕНІ БАСЫҢЫЗ…",
        "coords": "БАТЫРМА КООРДИНАТТАРЫ", "play": "Ойнау", "leave": "Шығу", "confirm": "Растау",
        "rclick": "Тінтуірдің оң жақ батырмасы", "save": "САҚТАУ", "reset": "ӘДЕПКІГЕ ҚАЙТАРУ",
        "ui_title": "Интерфейс", "ui_sub": "Қолданба тақырыбы мен тілін таңдаңыз.",
        "appearance": "СЫРТҚЫ КӨРІНІС", "theme": "Тақырып", "language": "Тіл",
        "sound_lbl": "Іске қосу дыбысы", "sound_n": "Дыбыс {0}", "sound_on": "Дыбысты қосу",
        "theme_Purple": "Күлгін", "theme_Black": "Қара", "theme_White": "Ақ",
        "ph_stopped": "ТОҚТАТЫЛДЫ", "ph_match": "МАТЧТА", "ph_leaving": "ШЫҒУ", "ph_lobby": "ЛОББИ",
        "sub_ready": "Дайын. Бастау үшін кезекті іске қосыңыз.",
        "sub_match": "Матч таймерінің аяқталуын күту.", "sub_leaving": "Матчтан шығу...",
        "sub_lobby": "Лоббиді күту.",
        "sub_failsafe": "Тоқтатылды: тінтуір сол жақ жоғарғы бұрышта (апаттық тоқтату).", "sub_error": "Қате: {0}",
        "note_default": "Өзгерістер келесі циклден бастап қолданылады.", "note_saved": "Баптаулар сақталды.",
        "note_defaults": "Әдепкі баптаулар қалпына келтірілді.", "note_numbers": "Қате: барлық өрістер сан болуы керек.",
        "note_hotkey": "Перне таңдалды: {0}", "note_copied": "Тінтуір координаттары көшірілді: {0}, {1}",
        "note_hk_err": "Жылдам перне қатесі: {0} (әкімші ретінде іске қосыңыз)",
        "note_cap_err": "Пернені оқу мүмкін болмады: {0}",
        "ab_pmin_lbl": "Үзіліс бастап (с)", "ab_pmax_lbl": "Үзіліс дейін (с)", "ab_amax_lbl": "Әрекет дейін (с)", "ab_pixel_on": "Тек матчта", "ab_marker_hint": "Белгі: тек матчта көрінетін нәрсеге (мысалы, денсаулық жолағына) меңзерді апарып, F11 басыңыз.", "marker_none": "белгіленбеген", "note_marker": "Матч белгісі қойылды: {0}, {1}  {2}", "note_marker_err": "Белгіні оқу мүмкін болмады: {0}", "key_mouse": "Тінтуір қозғалысы", "nav_team": "ТОП БАҚЫЛАУЫ", "td_title": "Топ бақылауы", "td_sub": "Ойын тек 4 ойыншының барлығы, сізді қоса алғанда, қатарынан 3 тексеруде қайтыс болғаны расталғанда ғана ерте аяқталады.", "td_enable": "Бүкіл топ қайтыс болғанда матчтан шығу", "td_signs": "ӘР ОЙЫНШЫНЫҢ ӨЛІМ БЕЛГІСІ", "td_player": "{0}-ойыншы", "td_popup": "Іске қосу терезесі (баспау)", "td_set": "ҚОЮ", "td_clear": "ТАЗАЛАУ", "td_hint": "«Қою» түймесін басып, 4 секунд ішінде ойындағы осы ойыншының анық көрнекі өлім белгісіне меңзерді апарыңыз. Іске қосу терезесі үшін — жаңа ойынды мезгілсіз бастайтын түймеге.", "td_state_off": "Тексеру өшірулі. Ойын тек таймермен аяқталады.", "td_state_incomplete": "4 ойыншының барлық белгісін қойыңыз, әйтпесе тексеру жұмыс істемейді ({0}/4 қойылған).", "td_state_ready": "Дайын: барлық 4 ойыншы қатарынан 3 тексеруде қайтыс болғанда ойын аяқталады.", "td_wait": "Меңзерді мынаған апарыңыз: {0}   {1}", "td_slot_set": "{0} сақталды: {1}, {2}  {3}", "sub_team_dead": "Барлық 4 ойыншы қайтыс болды. Матчтан шығу...", "survey_auto": "Сауалнама экранын автоматты өткізу («Өткізіп жіберу» түймесі)", "note_survey_skipped": "Сауалнама экраны табылды: «Өткізіп жіберу» басылды.", "nav_antiban": "АНТИБАН", "ab_title": "Антибан",
        "ab_sub": "Матч кезінде кездейсоқ бір мезгілдегі әрекеттер: жүру, жүгіру, секіру, шерту және тінтуір қозғалысы.",
        "ab_enable": "Антибанды қосу", "ab_keys": "БАСЫЛАТЫН ПЕРНЕЛЕР",
        "key_w": "W", "key_a": "A", "key_s": "S", "key_d": "D", "key_shift": "Shift",
        "key_space": "Бос орын", "key_lmb": "Тінтуірдің сол жақ батырмасы", "key_custom": "Өз пернеңіз",
        "note_custom_key": "Өз пернеңіз таңдалды: {0}",
        "ab_timing": "ӘРЕКЕТ УАҚЫТЫ", "ab_delay_lbl": "Play-ден кейін бастау (с)", "ab_save": "АНТИБАНДЫ САҚТАУ",
        "note_ab_saved": "Антибан баптаулары сақталды.", "note_ab_range": "Қате: мин. үзіліс макс. үзілістен үлкен болмауы керек.",
        "version": "Нұсқа 1.4", "tg_channel": "Telegram арнасы",
    },
}


def t(key, *args):
    s = TR.get(cfg.get("language", "English"), {}).get(key) or EN.get(key, key)
    return s.format(*args) if args else s


_i18n = []   # (виджет, ключ, аргументы)


def L(widget, key, *args):
    """Привязывает текст виджета к ключу перевода."""
    _i18n.append((widget, key, args))
    widget.configure(text=t(key, *args))
    return widget


state = {"running": False, "phase": "ph_stopped", "sub": "sub_ready", "sub_arg": None,
         "remaining": 0.0, "rounds": 0}
stop_ev = threading.Event()


def fmt(sec):
    sec = max(0, int(round(sec)))
    return f"{sec // 60:02d}:{sec % 60:02d}"


def num(v):
    v = float(v)
    return int(v) if v == int(v) else v


# ---------------- логика ----------------
AB_BASE = ("w", "a", "s", "d", "shift", "space", "lmb", "mouse")
AB_KEYS = AB_BASE + ("custom",)

# --- ввод через SendInput со сканкодами (так клавиши понимают игры; pyautogui шлёт только виртуальные коды) ---
if sys.platform == "win32":
    from ctypes import wintypes as _wt
    _ULONG_PTR = ctypes.c_size_t

    class _KEYBDINPUT(ctypes.Structure):
        _fields_ = [("wVk", _wt.WORD), ("wScan", _wt.WORD), ("dwFlags", _wt.DWORD),
                    ("time", _wt.DWORD), ("dwExtraInfo", _ULONG_PTR)]

    class _MOUSEINPUT(ctypes.Structure):
        _fields_ = [("dx", _wt.LONG), ("dy", _wt.LONG), ("mouseData", _wt.DWORD),
                    ("dwFlags", _wt.DWORD), ("time", _wt.DWORD), ("dwExtraInfo", _ULONG_PTR)]

    class _INPUTUNION(ctypes.Union):
        _fields_ = [("ki", _KEYBDINPUT), ("mi", _MOUSEINPUT)]

    class _INPUT(ctypes.Structure):
        _fields_ = [("type", _wt.DWORD), ("u", _INPUTUNION)]


def _send_input(inp):
    try:
        ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))
    except Exception:
        pass


def send_scan(scan, down, extended=False):
    """Нажатие/отпускание клавиши по сканкоду (KEYEVENTF_SCANCODE)."""
    if sys.platform != "win32":
        return
    inp = _INPUT(type=1)
    inp.u.ki = _KEYBDINPUT(0, scan, 0x0008 | (0 if down else 0x0002) | (0x0001 if extended else 0), 0, 0)
    _send_input(inp)


def send_mouse(dx=0, dy=0, flags=0x0001):
    """Событие мыши. flags: 0x0001 — сдвиг (относительный), 0x0002/0x0004 — ЛКМ вниз/вверх."""
    if sys.platform != "win32":
        return
    inp = _INPUT(type=0)
    inp.u.mi = _MOUSEINPUT(int(dx), int(dy), 0, flags, 0, 0)
    _send_input(inp)


AB_SCAN = {"w": (0x11, False), "a": (0x1E, False), "s": (0x1F, False), "d": (0x20, False),
           "shift": (0x2A, False), "space": (0x39, False)}
EXTENDED_VKS = {0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x2D, 0x2E, 0x5B}


def ab_scan(k):
    """(сканкод, extended) для пункта антибана или None."""
    if k in AB_SCAN:
        return AB_SCAN[k]
    if k == "custom":
        try:
            vk = vk_code(cfg.get("ab_custom_key"))
            sc = ctypes.windll.user32.MapVirtualKeyW(vk, 0) if vk else 0
            return (sc, vk in EXTENDED_VKS) if sc else None
        except Exception:
            return None
    return None


ab_used = [False]   # запускался ли антибан в этом запуске
ab_down = set()     # что сейчас удерживается


def ab_press(k):
    if k == "lmb":
        send_mouse(0, 0, 0x0002)
        ab_down.add(k)
        return
    sc = ab_scan(k)
    if sc:
        send_scan(sc[0], True, sc[1])
        ab_down.add(k)


def ab_release(k):
    if k == "lmb":
        if k in ab_down:
            send_mouse(0, 0, 0x0004)
    else:
        sc = ab_scan(k)
        if sc:
            send_scan(sc[0], False, sc[1])
    ab_down.discard(k)


def release_all():
    """Отпускает всё, что мог держать антибан (клавиши и ЛКМ)."""
    for k in ("w", "a", "s", "d", "shift", "space", "custom", "lmb"):
        try:
            ab_release(k)
        except Exception:
            pass


def in_match():
    """Совпадает ли цвет пикселя-маркера матча. Если маркер не задан или выключен — считаем, что матч идёт."""
    px = cfg.get("ab_pixel")
    if not cfg.get("ab_pixel_on") or not px:
        return True
    try:
        c = ImageGrab.grab(bbox=(px[0], px[1], px[0] + 1, px[1] + 1)).convert("RGB").getpixel((0, 0))
        want = hex_rgb(px[2])
        return all(abs(c[i] - want[i]) <= 40 for i in range(3))
    except Exception:
        return True


def _cursor_xy():
    try:
        pt = _wt.POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        return pt.x, pt.y
    except Exception:
        return None


def antiban_loop(end_time, stop, start_at):
    """Несколько независимых «каналов» работают одновременно и случайно: движение (W/A/S/D, в том числе
    сочетания), бег (Shift), прыжок, ЛКМ, своя клавиша и плавное движение мыши."""
    ab_used[0] = True
    on = {k for k in AB_KEYS if cfg["ab_keys"].get(k)}
    pmin = max(0.05, float(cfg["ab_pmin"]))
    pmax = max(pmin, float(cfg["ab_pmax"]))
    amax = max(0.3, float(cfg["ab_amax"]))
    rnd = random.uniform
    move_keys = [k for k in ("w", "a", "s", "d") if k in on]
    opposite = {"w": "s", "s": "w", "a": "d", "d": "a"}
    mv = {"keys": [], "until": 0.0, "next": start_at + rnd(0, 0.5)}
    sh = {"on": False, "t": start_at + rnd(0, pmax)}
    taps = [{"k": k, "down": False, "t": start_at + rnd(0, pmax * sc), "scale": sc}
            for k, sc in (("space", 2.0), ("lmb", 2.5), ("custom", 3.0))
            if k in on and (k != "custom" or ab_scan("custom"))]
    ms = {"until": 0.0, "next": start_at + rnd(0, 0.5), "vx": 0.0, "vy": 0.0, "ax": 0.0, "ay": 0.0,
          "tx": 0, "ty": 0, "last": time.time()}
    start_pos = _cursor_xy() if "mouse" in on else None
    active, next_check = True, 0.0

    def step_move(now):
        if not move_keys:
            return
        if mv["keys"]:
            if now >= mv["until"]:
                for k in mv["keys"]:
                    ab_release(k)
                mv["keys"] = []
                mv["next"] = now + (0.0 if random.random() < 0.3 else rnd(pmin * 0.3, pmax))
        elif now >= mv["next"]:
            first = random.choices(move_keys, [3 if k == "w" else 1 for k in move_keys])[0]
            combo = [first]
            if random.random() < 0.45:
                others = [k for k in move_keys if k not in (first, opposite[first])]
                if others:
                    combo.append(random.choice(others))
            for k in combo:
                ab_press(k)
            mv["keys"] = combo
            mv["until"] = now + rnd(min(0.4, amax), amax)

    def step_shift(now):
        if "shift" not in on:
            return
        if sh["on"]:
            if now >= sh["t"]:
                ab_release("shift")
                sh["on"], sh["t"] = False, now + rnd(pmin, pmax * 2)
        elif now >= sh["t"]:
            ab_press("shift")
            sh["on"], sh["t"] = True, now + rnd(0.8, max(1.0, amax * 2))

    def step_tap(c, now):
        if c["down"]:
            if now >= c["t"]:
                ab_release(c["k"])
                c["down"], c["t"] = False, now + rnd(pmin, pmax * c["scale"])
        elif now >= c["t"]:
            if c["k"] == "lmb":
                pos = _cursor_xy()
                if pos and popup_guard(*pos):      # курсор над окном запуска новой катки — не кликаем
                    c["t"] = now + 0.5
                    return
            ab_press(c["k"])
            c["down"], c["t"] = True, now + rnd(0.05, 0.18)

    def step_mouse(now):
        if "mouse" not in on:
            return
        dt = min(0.1, now - ms["last"])
        ms["last"] = now
        if now < ms["until"]:
            ms["ax"] += ms["vx"] * dt
            ms["ay"] += ms["vy"] * dt
            ix, iy = int(ms["ax"]), int(ms["ay"])
            if ix or iy:
                ms["ax"] -= ix
                ms["ay"] -= iy
                send_mouse(ix, iy, 0x0001)
                ms["tx"] += ix
                ms["ty"] += iy
        elif now >= ms["next"]:
            vx = rnd(120, 650) * random.choice((-1, 1))
            vy = rnd(0, 120) * random.choice((-1, 1))
            if ms["tx"] > 500:        # не уводим курсор/камеру слишком далеко в одну сторону
                vx = -abs(vx)
            elif ms["tx"] < -500:
                vx = abs(vx)
            if ms["ty"] > 120:
                vy = -abs(vy)
            elif ms["ty"] < -120:
                vy = abs(vy)
            dur = rnd(min(0.25, amax), amax)
            ms.update(vx=vx, vy=vy, until=now + dur,
                      next=now + dur + (rnd(0, pmax * 0.5) if random.random() < 0.6 else 0.0))

    try:
        while not stop.is_set() and not stop_ev.is_set():
            now = time.time()
            if now >= end_time - 1.0:
                break
            if now < start_at:
                time.sleep(0.1)
                continue
            if now >= next_check:
                next_check = now + 0.5
                was_active, active = active, in_match()
                if was_active and not active:     # матч закончился / мы в меню — всё отпускаем и ждём
                    release_all()
                    mv["keys"], sh["on"] = [], False
                    for c in taps:
                        c["down"] = False
            if not active:
                ms["last"] = now
                time.sleep(0.1)
                continue
            step_move(now)
            step_shift(now)
            for c in taps:
                step_tap(c, now)
            step_mouse(now)
            time.sleep(0.015)
    finally:
        release_all()
        if start_pos:                              # возвращаем курсор, чтобы он не «уполз» в угол экрана
            try:
                ctypes.windll.user32.SetCursorPos(start_pos[0], start_pos[1])
            except Exception:
                pass


TD_TOL = 32          # допуск по цвету (на канал) для признака смерти
TD_CHECKS = 3        # сколько проверок подряд должны подтвердить смерть всех 4 игроков
TD_INTERVAL = 0.8    # пауза между проверками (сек)
TD_START = 20.0      # первые секунды после клика по Play не проверяем (поиск игры / загрузка)
POPUP_R = 80         # радиус защитной зоны вокруг окна преждевременного запуска (px)
_BOX = getattr(Image, "Resampling", Image).BOX


def td_ready():
    """Проверка смерти работает только если включена и заданы признаки ВСЕХ 4 игроков."""
    slots = cfg.get("td_slots") or []
    return bool(cfg.get("td_enabled")) and len(slots) == 4 and all(slots)


def team_dead():
    """True — у всех 4 игроков на ОДНОМ кадре виден явный признак смерти.
    Если игрок жив, признак не виден или состояние определить нельзя — False (катка продолжается)."""
    if not td_ready():
        return False
    try:
        shot = ImageGrab.grab().convert("RGB")
    except Exception:
        return False
    for x, y, col in cfg["td_slots"]:
        try:
            c = shot.crop((x - 2, y - 2, x + 3, y + 3)).resize((1, 1), _BOX).getpixel((0, 0))
            want = hex_rgb(col)
        except Exception:
            return False
        if any(abs(c[i] - want[i]) > TD_TOL for i in range(3)):
            return False
    return True


def popup_guard(x, y):
    """True, если точка (x, y) попадает в зону окна преждевременного запуска новой катки (туда не кликаем)."""
    z = cfg.get("td_popup")
    return bool(z) and math.hypot(x - z[0], y - z[1]) < POPUP_R


CLICK_DWELL = 0.35     # сколько курсор «стоит» над кнопкой перед кликом (игра успевает её подсветить)
CLICK_HOLD = 0.09      # сколько кнопка мыши остаётся нажатой
CLICK_ATTEMPTS = 3     # попыток клика, если кнопка не отреагировала (только при verify=True)


def hover_to(pos, dwell=CLICK_DWELL):
    """Подводит курсор к кнопке «живым» движением (а не телепортом) и ждёт, пока она подсветится."""
    x, y = int(pos[0]), int(pos[1])
    pyautogui.moveTo(x - 16, y - 10, duration=0.12)
    pyautogui.moveTo(x, y, duration=0.18)
    time.sleep(dwell)
    send_mouse(1, 0, 0x0001)          # микродвижение: гарантированное событие наведения для игры
    time.sleep(0.03)
    send_mouse(-1, 0, 0x0001)
    time.sleep(0.05)


def press_mouse(button="left"):
    pyautogui.mouseDown(button=button)
    time.sleep(CLICK_HOLD)
    pyautogui.mouseUp(button=button)


def _region(pos, r=80):
    x, y = int(pos[0]), int(pos[1])
    return ImageGrab.grab(bbox=(max(0, x - r), max(0, y - r), x + r, y + r)).convert("RGB")


def _region_diff(a, b):
    return sum(ImageStat.Stat(ImageChops.difference(a, b)).mean) / 3.0


def click_at(pos, button="left", robust=True, verify=False, guard=True):
    """Клик бота. robust — навести, подождать подсветку, нажать с удержанием (игра не пропускает такие клики);
    verify — после клика проверить, что картинка вокруг кнопки изменилась, и при необходимости повторить.
    guard — не кликать по зоне окна преждевременного запуска новой катки."""
    if guard and popup_guard(pos[0], pos[1]):
        log_error(f"Click at {list(pos)} skipped: it is inside the popup no-click zone")
        return False
    if not robust:
        pyautogui.click(pos[0], pos[1], button=button)
        return True
    for attempt in range(CLICK_ATTEMPTS if verify else 1):
        if stop_ev.is_set():
            return False
        hover_to(pos, CLICK_DWELL + 0.3 * attempt)
        before = None
        if verify:
            try:
                before = _region(pos)
            except Exception:
                verify = False
        press_mouse(button)
        if not verify:
            return True
        time.sleep(0.9)
        try:
            if _region_diff(before, _region(pos)) > 6.0:     # кнопка/меню изменились — клик сработал
                return True
        except Exception:
            return True
        log_error(f"Click at {list(pos)} had no visible effect (attempt {attempt + 1}/{CLICK_ATTEMPTS})")
    return False


def countdown(sec, phase, sub, antiban=False, death_watch=False):
    state["phase"], state["sub"], state["sub_arg"] = phase, sub, None
    now = time.time()
    end = now + sec
    use_ab = antiban and cfg.get("ab_enabled") and any(cfg["ab_keys"].get(k) for k in AB_KEYS)
    td_on = death_watch and td_ready()
    next_td, td_hits = now + TD_START, 0
    ab_stop, ab_thread = threading.Event(), None
    if use_ab:
        ab_thread = threading.Thread(target=antiban_loop, daemon=True,
                                     args=(end, ab_stop, now + max(0.0, float(cfg["ab_delay"]))))
        ab_thread.start()
    try:
        while True:
            if stop_ev.is_set():
                return False
            rem = end - time.time()
            if rem <= 0:
                state["remaining"] = 0
                return True
            state["remaining"] = rem
            if td_on and time.time() >= next_td:
                next_td = time.time() + TD_INTERVAL
                td_hits = td_hits + 1 if team_dead() else 0     # любая неудача/неизвестность сбрасывает счётчик
                if td_hits >= TD_CHECKS:                         # 3 подряд: погибли все 4
                    state["team_dead"] = True
                    state["remaining"] = 0
                    return True                                  # finally ниже сразу останавливает антибан
            time.sleep(0.1)
    finally:
        ab_stop.set()
        if ab_thread is not None:
            ab_thread.join(timeout=2.0)


# ---------- экран опроса «Нам интересно узнать ваше мнение» -> кнопка «Пропустить» ----------
SURVEY_REF_H = 1078.0    # высота эталонного скриншота, по нему заданы размеры ниже
survey_lock = threading.Lock()


def _survey_masks(shot):
    """Маски светлого (кнопка «Пропустить»), серого («Отправить» неактивна) и синего (кружки оценок)."""
    r, g, b = shot.split()
    mn = ImageChops.darker(ImageChops.darker(r, g), b)
    mx = ImageChops.lighter(ImageChops.lighter(r, g), b)
    spread = ImageChops.subtract(mx, mn)
    light = ImageChops.darker(mn.point(lambda v: 255 if v > 215 else 0), spread.point(lambda v: 255 if v < 40 else 0))
    grey = ImageChops.darker(ImageChops.darker(mn.point(lambda v: 255 if v > 165 else 0),
                                               mx.point(lambda v: 255 if v <= 218 else 0)),
                             spread.point(lambda v: 255 if v < 30 else 0))
    blue = ImageChops.darker(ImageChops.darker(b.point(lambda v: 255 if v > 140 else 0),
                                               r.point(lambda v: 255 if v < 80 else 0)),
                             ImageChops.subtract(b, r).point(lambda v: 255 if v > 100 else 0))
    return light, grey, blue


def _integral(vals, w, h):
    ii = [0] * ((w + 1) * (h + 1))
    for y in range(h):
        run, row, prev = 0, (y + 1) * (w + 1), y * (w + 1)
        for x in range(w):
            run += vals[y * w + x]
            ii[row + x + 1] = ii[prev + x + 1] + run
    return ii


def find_survey_skip(shot):
    """Ищет экран опроса и возвращает (x, y) центра кнопки «Пропустить» или None.
    Нужно сразу всё: светлая кнопка слева, серая кнопка справа и ряд синих кружков выше них.
    Размеры масштабируются по высоте экрана, поэтому работает при любом разрешении."""
    W, H = shot.size
    s = H / SURVEY_REF_H
    ds = max(3, int(round(H / 135)))
    SW, SH = W // ds, H // ds
    bw, bh = max(3, int(round(245 * s / ds))), max(2, int(round(56 * s / ds)))
    gw, shift = max(3, int(round(228 * s / ds))), int(round(270 * s / ds))
    if SW <= shift + gw + 1 or SH <= bh + 1:
        return None
    light, grey, blue = _survey_masks(shot)
    ls = light.resize((SW, SH), _BOX)
    gs = grey.resize((SW, SH), _BOX)
    LI, GI = _integral(list(ls.getdata()), SW, SH), _integral(list(gs.getdata()), SW, SH)
    stride = SW + 1
    lden, gden = bw * bh * 255.0, gw * bh * 255.0
    best = None
    for y in range(0, SH - bh):
        r0, r1 = y * stride, (y + bh) * stride
        for x in range(0, SW - shift - gw):
            lv = (LI[r1 + x + bw] - LI[r0 + x + bw] - LI[r1 + x] + LI[r0 + x]) / lden
            if lv < 0.5:
                continue
            gx = x + shift
            gv = (GI[r1 + gx + gw] - GI[r0 + gx + gw] - GI[r1 + gx] + GI[r0 + gx]) / gden
            if gv < 0.5:
                continue
            if best is None or lv + gv > best[0]:
                best = (lv + gv, x, y)
    if best is None:
        return None
    _, bx, by = best
    x0, y0 = bx * ds, by * ds
    cx = x0 + 248 * s
    box = (int(max(0, cx - 360 * s)), int(max(0, y0 - 420 * s)), int(min(W, cx + 360 * s)), int(max(1, y0 - 120 * s)))
    if box[2] <= box[0] or box[3] <= box[1]:
        return None
    if ImageStat.Stat(blue.crop(box)).mean[0] / 255.0 < 0.08:      # кружков оценок нет — это не опрос
        return None
    return int(x0 + bw * ds / 2), int(y0 + bh * ds / 2)


def survey_skip_once(confirm=True):
    """Один проход: если на экране опрос — нажимает «Пропустить». Возвращает True, если нажал."""
    if not survey_lock.acquire(blocking=False):
        return False
    try:
        pos = find_survey_skip(ImageGrab.grab().convert("RGB"))
        if pos and confirm:                      # подтверждаем вторым кадром, чтобы не среагировать на случайность
            time.sleep(0.35)
            pos = find_survey_skip(ImageGrab.grab().convert("RGB"))
        if not pos:
            return False
        pyautogui.click(pos[0], pos[1])
        try:
            root.after(0, lambda: set_note("note_survey_skipped"))
        except Exception:
            pass
        return True
    except Exception:
        log_error("Survey skip failed:\n" + traceback.format_exc())
        return False
    finally:
        survey_lock.release()


def survey_skip_now():
    """Перед кликом по Play: пропускает опрос (если их подряд несколько — до трёх)."""
    if not cfg.get("auto_skip_survey", True):
        return
    for _ in range(3):
        if not survey_skip_once(True):
            return
        time.sleep(0.8)


def survey_watcher():
    """Фоновая проверка, пока бот запущен: появился опрос — пропускаем."""
    last = 0.0
    while not quitting:
        time.sleep(1.5)
        if cfg.get("auto_skip_survey", True) and state["running"] and time.time() - last > 3.0:
            if survey_skip_once(True):
                last = time.time()


def run():
    err = None
    try:
        while not stop_ev.is_set():
            survey_skip_now()          # если на экране опрос — сначала пропускаем его, иначе клик по Play не сработает
            click_at(cfg["play"], guard=False)
            if not countdown(cfg["match_min"] * 60, "ph_match", "sub_match", antiban=True, death_watch=True):
                break
            # сюда доходим уже с остановленным антибаном (движение, мышь и ЛКМ отпущены)
            dead = state.pop("team_dead", False)
            state["phase"], state["sub"], state["sub_arg"] = "ph_leaving", ("sub_team_dead" if dead else "sub_leaving"), None
            click_at(cfg["rmb"], "right", robust=False)
            time.sleep(0.5)
            pyautogui.press("esc")
            time.sleep(1)
            click_at(cfg["leave"])
            time.sleep(1.2)
            click_at(cfg["confirm"], verify=True)     # кнопка выхода: наводим, ждём подсветку, кликаем и проверяем результат
            if not countdown(cfg["lobby_sec"], "ph_lobby", "sub_lobby"):
                break
            state["rounds"] += 1
    except pyautogui.FailSafeException:
        err = ("sub_failsafe", None)
    except Exception as e:
        log_error(traceback.format_exc())
        err = ("sub_error", str(e))
    finally:
        key, arg = err if err else ("sub_ready", None)
        # сначала снимаем «запущено», чтобы клавиша старт/стоп сразу работала снова
        state.update(running=False, phase="ph_stopped", remaining=0, sub=key, sub_arg=arg)
        if not quitting:
            play_stop_sound()
        if ab_used[0]:
            ab_used[0] = False
            release_all()


run_thread = None


def toggle():
    global run_thread
    if state["running"] and run_thread is not None and run_thread.is_alive():
        stop_ev.set()
        return
    # Звук проигрывается только при запуске.
    play_toggle_sound()
    stop_ev.clear()
    state["running"] = True
    run_thread = threading.Thread(target=run, daemon=True)
    run_thread.start()


def quit_app():
    global quitting
    quitting = True
    stop_ev.set()
    try:
        if capture_hook is not None:
            keyboard.unhook(capture_hook)
    except Exception:
        pass
    try:
        keyboard.unhook_all_hotkeys()
    except Exception:
        pass
    root.destroy()


# ---------------- иконки (рисуются через Pillow со сглаживанием) ----------------
SS = 8  # во сколько раз рисуем крупнее, чтобы потом сгладить
RESAMPLE = getattr(Image, "Resampling", Image).LANCZOS


def hex_rgb(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def lerp_hex(a, b, t):
    t = max(0.0, min(1.0, t))
    ra, rb = hex_rgb(a), hex_rgb(b)
    return "#%02x%02x%02x" % tuple(int(round(ra[i] + (rb[i] - ra[i]) * t)) for i in range(3))


def _canvas(px):
    img = Image.new("RGBA", (px * SS, px * SS), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def _stroke(d, pts, width, fill, caps=(True, True)):
    """Толстая линия со скруглёнными стыками и (по желанию) скруглёнными концами."""
    w = max(1, int(round(width)))
    d.line(pts, fill=fill, width=w, joint="curve")
    r = w / 2.0
    for i, (x, y) in enumerate(pts):
        if (i == 0 and not caps[0]) or (i == len(pts) - 1 and not caps[1]):
            continue
        d.ellipse((x - r, y - r, x + r, y + r), fill=fill)


def icon_stack(px, t, color):
    """Три слоя. При наведении слои раздвигаются."""
    img, d = _canvas(px)
    s = px * SS / 24.0
    sp = 1.4 * t
    col = hex_rgb(color) + (255,)

    def pts(points, dy):
        return [(x * s, (y + dy) * s) for x, y in points]

    dia = pts([(12, 2.8), (20.2, 7.1), (12, 11.4), (3.8, 7.1)], -sp)
    d.polygon(dia, fill=col)
    _stroke(d, dia + [dia[0]], 1.8 * s, col)
    _stroke(d, pts([(4.2, 12.9), (12, 17.0), (19.8, 12.9)], 0), 2.2 * s, col)
    _stroke(d, pts([(4.2, 17.4), (12, 21.5), (19.8, 17.4)], sp), 2.2 * s, col)
    return img.resize((px, px), RESAMPLE)


def icon_gear(px, angle, color):
    """Шестерёнка. angle — поворот в градусах."""
    S = px * SS
    s = S / 24.0
    mask = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(mask)
    cx = cy = 12 * s
    r_out, r_in, teeth = 10.4 * s, 7.7 * s, 8
    pts = []
    for i in range(teeth):
        a = i * 360.0 / teeth + angle
        for da, r in ((-17, r_in), (-10, r_out), (10, r_out), (17, r_in)):
            rad = math.radians(a + da)
            pts.append((cx + r * math.cos(rad), cy + r * math.sin(rad)))
    d.polygon(pts, fill=255)
    _stroke(d, pts + [pts[0]], 1.1 * s, 255)          # слегка скругляем зубья
    hole = 3.6 * s
    d.ellipse((cx - hole, cy - hole, cx + hole, cy + hole), fill=0)
    img = Image.new("RGBA", (S, S), hex_rgb(color) + (255,))
    img.putalpha(mask)
    return img.resize((px, px), RESAMPLE)


def icon_link(px, t, color):
    """Капсула из двух половинок. При наведении половинки расходятся, правая «загорается»."""
    img, d = _canvas(px)
    s = px * SS / 24.0
    sep = 1.7 * t
    r, cy, w = 5.4, 12.0, 3.2
    rgb = hex_rgb(color)
    full = rgb + (255,)
    dim = rgb + (int(95 + 160 * t),)

    def arc(cx, sign):
        out = []
        for k in range(25):
            th = math.radians(-90 + sign * 180.0 * k / 24)
            out.append((cx + r * math.cos(th), cy + r * math.sin(th)))
        return out

    lx, rx = 8.2 - sep, 15.8 + sep
    left = [(11.3 - sep, cy - r), (lx, cy - r)] + arc(lx, -1)[1:-1] + [(lx, cy + r), (11.3 - sep, cy + r)]
    right = [(12.7 + sep, cy - r), (rx, cy - r)] + arc(rx, +1)[1:-1] + [(rx, cy + r), (12.7 + sep, cy + r)]
    _stroke(d, [(x * s, y * s) for x, y in left], w * s, full, caps=(False, False))
    _stroke(d, [(x * s, y * s) for x, y in right], w * s, dim, caps=(False, False))
    return img.resize((px, px), RESAMPLE)


def icon_eye(px, phase, color):
    """Глаз. Зрачок плавно «смотрит» влево-вправо (phase — градусы, 0..360)."""
    img, d = _canvas(px)
    s = px * SS / 24.0
    col = hex_rgb(color) + (255,)

    def bez(p0, c, p1, n=18):
        return [((1 - u) ** 2 * p0[0] + 2 * (1 - u) * u * c[0] + u ** 2 * p1[0],
                 (1 - u) ** 2 * p0[1] + 2 * (1 - u) * u * c[1] + u ** 2 * p1[1]) for u in (i / n for i in range(n + 1))]

    top = bez((2.2, 12), (12, 2.4), (21.8, 12))
    bottom = bez((21.8, 12), (12, 21.6), (2.2, 12))
    pts = [(x * s, y * s) for x, y in top + bottom[1:]]
    _stroke(d, pts, 2.0 * s, col)
    px_off = 2.6 * math.sin(math.radians(phase))
    r = 3.3 * s
    cx, cy = (12 + px_off) * s, 12 * s
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col)
    return img.resize((px, px), RESAMPLE)


def icon_shield(px, phase, color):
    """Щит с галочкой. phase (градусы, 0..360) — фаза «пульса»: щит увеличивается, приподнимается
    и покачивается, после полного цикла возвращается в исходное положение."""
    img, d = _canvas(px)
    s = px * SS / 24.0
    pulse = (1 - math.cos(math.radians(phase))) / 2          # 0 -> 1 -> 0
    sc, lift = 0.92 * (1 + 0.17 * pulse), -0.8 * pulse   # 0.92 — запас, чтобы при увеличении не обрезался край
    rot = math.radians(12 * math.sin(math.radians(phase * 2)))  # покачивание влево-вправо
    cr, sr = math.cos(rot), math.sin(rot)
    col = hex_rgb(color) + (255,)

    def pt(x, y):
        dx, dy = (x - 12) * sc, (y - 12) * sc
        return ((12 + dx * cr - dy * sr) * s, (12 + dx * sr + dy * cr + lift) * s)

    def bez(p0, c, p1, n=14):
        return [((1 - u) ** 2 * p0[0] + 2 * (1 - u) * u * c[0] + u ** 2 * p1[0],
                 (1 - u) ** 2 * p0[1] + 2 * (1 - u) * u * c[1] + u ** 2 * p1[1]) for u in (i / n for i in range(1, n + 1))]

    shape = [(12, 2.6), (19.4, 5.3), (19.4, 11.2)]
    shape += bez((19.4, 11.2), (19.0, 17.6), (12, 21.6))
    shape += bez((12, 21.6), (5.0, 17.6), (4.6, 11.2))
    shape += [(4.6, 5.3)]
    pts = [pt(x, y) for x, y in shape]
    _stroke(d, pts + [pts[0]], 2.0 * s, col)
    _stroke(d, [pt(8.3, 11.8), pt(10.9, 14.4), pt(15.9, 8.9)], 2.0 * s, col)
    return img.resize((px, px), RESAMPLE)


def render_check(px, p, hover, c_line, c_acc, c_field, c_mark):
    """Скруглённый чекбокс в стиле интерфейса. p: 0..1 — прогресс галочки."""
    S = px * SS
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    border = lerp_hex(c_line, c_acc, max(p, 0.75 if hover else 0))
    fill = lerp_hex(c_field, c_acc, p)
    rad = 5 * SS
    d.rounded_rectangle((0, 0, S - 1, S - 1), radius=rad, fill=border)
    inset = int(1.6 * SS)
    d.rounded_rectangle((inset, inset, S - 1 - inset, S - 1 - inset), radius=rad - inset // 2, fill=fill)
    q = max(0.0, min(1.0, (p - 0.25) / 0.75))
    if q > 0:
        k = S / 18.0
        a, b, c = (4.6 * k, 9.4 * k), (7.8 * k, 12.6 * k), (13.6 * k, 5.8 * k)
        l1 = math.dist(a, b)
        l2 = math.dist(b, c)
        cut = q * (l1 + l2)
        path = [a]
        if cut <= l1:
            f = cut / l1
            path.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
        else:
            f = (cut - l1) / l2
            path += [b, (b[0] + (c[0] - b[0]) * f, b[1] + (c[1] - b[1]) * f)]
        _stroke(d, path, 2.3 * k, hex_rgb(c_mark) + (255,))
    return img.resize((px, px), RESAMPLE)


_FONT_CACHE = {}


def load_font(size, bold=True):
    key = (size, bold)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    names = (("segoeuib.ttf", "seguisb.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf") if bold
             else ("segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"))
    font = None
    for name in names:
        try:
            font = ImageFont.truetype(name, size)
            break
        except Exception:
            continue
    _FONT_CACHE[key] = font
    return font


def render_text(text, px, color, underline=False, bold=True, slide=None):
    """Гладкий (не пиксельный) текст. Высота и базовая линия зависят только от px,
    поэтому разные надписи выстраиваются ровно. Возвращает PIL-картинку или None."""
    font = load_font(px * SS, bold)
    if font is None:
        return None
    w = int(font.getlength(text) + 2 * SS)
    w += (-w) % SS
    h = int(px * SS * 1.5)
    h += (-h) % SS
    base = int(px * SS * 1.12)
    if slide is not None:   # запас снизу и сдвиг базовой линии для анимации «выезда» (высота всегда одинаковая)
        h += int(6 * SS)
        base += int(slide * SS)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    rgba = hex_rgb(color) + (255,)
    d.text((SS, base), text, font=font, fill=rgba, anchor="ls")
    if underline:
        y = base + int(0.2 * px * SS)
        d.line([(SS, y), (w - SS, y)], fill=rgba, width=max(1, int(0.09 * px * SS)))
    return img.resize((w // SS, h // SS), RESAMPLE)


def render_winbtn(kind, w, h, bg, glyph):
    """Кнопка управления окном: скруглённая плашка + гладкий значок."""
    img = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, w * SS - 1, h * SS - 1), radius=8 * SS, fill=bg)
    cx, cy = w * SS / 2.0, h * SS / 2.0
    g = hex_rgb(glyph) + (255,)
    lw = 1.7 * SS
    u = SS
    if kind == "min":
        _stroke(d, [(cx - 5 * u, cy + 1 * u), (cx + 5 * u, cy + 1 * u)], lw, g)
    elif kind == "max":
        d.rounded_rectangle((cx - 5 * u, cy - 5 * u, cx + 5 * u, cy + 5 * u), radius=2.5 * u,
                            outline=g, width=int(lw))
    elif kind == "restore":
        d.rounded_rectangle((cx - 5 * u, cy - 3 * u, cx + 3 * u, cy + 5 * u), radius=2 * u,
                            outline=g, width=int(lw))
        _stroke(d, [(cx - 2 * u, cy - 3 * u), (cx - 2 * u, cy - 5 * u), (cx + 5 * u, cy - 5 * u),
                    (cx + 5 * u, cy + 2 * u), (cx + 3.2 * u, cy + 2 * u)], lw, g)
    else:  # close
        _stroke(d, [(cx - 4.5 * u, cy - 4.5 * u), (cx + 4.5 * u, cy + 4.5 * u)], lw, g)
        _stroke(d, [(cx - 4.5 * u, cy + 4.5 * u), (cx + 4.5 * u, cy - 4.5 * u)], lw, g)
    return img.resize((w, h), RESAMPLE)


# ---------------- окно с собственной шапкой ----------------
# Убираем системный заголовок Windows, оставляя обычное окно в панели задач.
root = tk.Tk()
root.title("PIRATE TOKEN BOT")
W, H = 940, 660
root.geometry(f"{W}x{H}+{(root.winfo_screenwidth() - W) // 2}+{(root.winfo_screenheight() - H) // 2}")
root.minsize(860, 640)
root.resizable(True, True)
root.configure(bg=P["BG"], highlightthickness=0, bd=0, relief="flat")
root.attributes("-topmost", True)

# иконка окна, панели задач и шапки — своя для каждой темы
ICON_FILES = {"Purple": "PIRATE_ICON", "Black": "PIRATE_ICON_BLACK", "White": "PIRATE_ICON_WHITE"}
_LANCZOS = getattr(Image, "Resampling", Image).LANCZOS


def load_icon_set(theme_name):
    """(картинка, путь к .ico) для темы; если файлов темы нет, берём фиолетовую."""
    for base in (ICON_FILES.get(theme_name, "PIRATE_ICON"), "PIRATE_ICON"):
        png = asset_path(base + ".png")
        if os.path.exists(png):
            return Image.open(png).convert("RGBA"), asset_path(base + ".ico")
    return None, None


try:
    _icon_img, _ = load_icon_set(cfg["theme"])
except Exception:
    _icon_img = None
    log_error("Could not load app icon:\n" + traceback.format_exc())

custom_widgets = []   # объекты со своим методом restyle() (иконки, чекбокс, ссылка)
dropdown_instances = []


def minimize():
    root.iconify()


def toggle_maximize():
    """Переключает обычный размер окна и развёртывание на весь экран."""
    try:
        if root.state() == "zoomed":
            root.state("normal")
            maximize_btn.set_kind("max")
        else:
            root.state("zoomed")
            maximize_btn.set_kind("restore")
    except tk.TclError:
        if root.attributes("-zoomed"):
            root.attributes("-zoomed", False)
            maximize_btn.set_kind("max")
        else:
            root.attributes("-zoomed", True)
            maximize_btn.set_kind("restore")


# шапка
topbar = TH(tk.Frame(root, height=40), bg="SIDE")
topbar.pack(fill="x")
topbar.pack_propagate(False)
logo_lbl = TH(tk.Label(topbar, bd=0, highlightthickness=0), bg="SIDE")
if _icon_img is not None:
    root._logo_photo = ImageTk.PhotoImage(_icon_img.resize((24, 24), getattr(Image, "Resampling", Image).LANCZOS))
    logo_lbl.configure(image=root._logo_photo)
    logo_lbl.pack(side="left", padx=(14, 0))
title_lbl = TH(tk.Label(topbar, text="PIRATE TOKEN BOT", font=(FONT, 8, "bold")), bg="SIDE", fg="MUT")
title_lbl.pack(side="left", padx=(8 if _icon_img is not None else 16, 16))


def apply_app_icon(theme_name):
    """Меняет иконку окна, панели задач и шапки под тему (иконка самого EXE-файла в проводнике остаётся фиолетовой)."""
    try:
        pil, ico = load_icon_set(theme_name)
        if pil is None:
            return
        if sys.platform == "win32" and ico and os.path.exists(ico):
            root.iconbitmap(default=ico)
        root._icon_photo = ImageTk.PhotoImage(pil.resize((64, 64), _LANCZOS))
        root.iconphoto(True, root._icon_photo)
        root._logo_photo = ImageTk.PhotoImage(pil.resize((24, 24), _LANCZOS))
        logo_lbl.configure(image=root._logo_photo)
        if not logo_lbl.winfo_manager():
            logo_lbl.pack(side="left", padx=(14, 0), before=title_lbl)
    except Exception:
        log_error("Could not apply app icon:\n" + traceback.format_exc())



class WinBtn(tk.Label):
    """Кнопка окна (свернуть / развернуть / закрыть) в стиле интерфейса, с плавной подсветкой."""
    BW, BH = 38, 26

    def __init__(self, parent, kind, cmd):
        super().__init__(parent, bd=0, highlightthickness=0, padx=0, pady=0, cursor="hand2")
        self.kind, self.cmd, self.p, self._job, self.hover = kind, cmd, 0.0, None, False
        self.bind("<Enter>", lambda e: self._hover(True))
        self.bind("<Leave>", lambda e: self._hover(False))
        self.bind("<Button-1>", lambda e: self.cmd())
        custom_widgets.append(self)
        self.restyle()

    def set_kind(self, kind):
        self.kind = kind
        self.restyle()

    def _hover(self, v):
        self.hover = v
        if self._job is None:
            self._job = self.after(16, self._tick)

    def _tick(self):
        self._job = None
        target = 1.0 if self.hover else 0.0
        self.p += (target - self.p) * 0.4
        if abs(target - self.p) < 0.03:
            self.p = target
        self.restyle()
        if self.p != target:
            self._job = self.after(16, self._tick)

    def restyle(self):
        close = self.kind == "close"
        bg = lerp_hex(P["BTN"], P["RED"] if close else P["HOVER"], self.p)
        glyph = lerp_hex(P["MUT"], ACT_FG if close else P["TXT"], self.p)
        self.img = ImageTk.PhotoImage(render_winbtn(self.kind, self.BW, self.BH, bg, glyph))
        self.configure(image=self.img, bg=P["SIDE"])


WinBtn(topbar, "close", lambda: quit_app()).pack(side="right", padx=(0, 10), pady=7)
maximize_btn = WinBtn(topbar, "max", lambda: toggle_maximize())
maximize_btn.pack(side="right", padx=(0, 6), pady=7)
WinBtn(topbar, "min", lambda: minimize()).pack(side="right", padx=(0, 6), pady=7)

# ---------- перетаскивание и растягивание окна без системной рамки ----------
# Окно двигаем/меняем напрямую через SetWindowPos (без модального цикла Windows и без root.geometry),
# поэтому нет рывков, «шлейфа» и вылетов.
EDGE, CORNER = 6, 14          # толщина зоны захвата края / угла, px
CURSORS = {"w": "size_we", "e": "size_we", "n": "size_ns", "s": "size_ns",
           "nw": "size_nw_se", "se": "size_nw_se", "ne": "size_ne_sw", "sw": "size_ne_sw"}
MIN_W, MIN_H = 860, 640
LIVE_CONTENT = False   # True — перерисовывать интерфейс прямо во время растягивания (может мерцать)
SWP_NOSIZE, SWP_NOMOVE, SWP_NOZORDER, SWP_NOACTIVATE, SWP_NOCOPYBITS = 0x0001, 0x0002, 0x0004, 0x0010, 0x0100

drag = {"on": False, "x": 0, "y": 0, "wx": 0, "wy": 0}
resize = {"mode": None, "cursor": "", "start": None}


def _win_api():
    import ctypes
    from ctypes import wintypes
    u = ctypes.windll.user32
    u.GetAncestor.restype = wintypes.HWND
    u.GetAncestor.argtypes = [wintypes.HWND, ctypes.c_uint]
    u.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    u.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
    u.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                               ctypes.c_int, ctypes.c_int, ctypes.c_uint]
    return ctypes, wintypes, u


def cursor_pos():
    if sys.platform == "win32":
        try:
            ctypes, wintypes, u = _win_api()
            pt = wintypes.POINT()
            u.GetCursorPos(ctypes.byref(pt))
            return pt.x, pt.y
        except Exception:
            pass
    return root.winfo_pointerx(), root.winfo_pointery()


def window_rect():
    """(left, top, right, bottom) окна на экране."""
    if sys.platform == "win32":
        try:
            ctypes, wintypes, u = _win_api()
            hwnd = u.GetAncestor(wintypes.HWND(root.winfo_id()), 2) or wintypes.HWND(root.winfo_id())
            r = wintypes.RECT()
            u.GetWindowRect(hwnd, ctypes.byref(r))
            return r.left, r.top, r.right, r.bottom
        except Exception:
            pass
    x, y = root.winfo_rootx(), root.winfo_rooty()
    return x, y, x + root.winfo_width(), y + root.winfo_height()


def move_window(x, y, w=None, h=None):
    """Двигает/меняет размер окна напрямую. Возвращает False, если не удалось."""
    if sys.platform == "win32":
        try:
            ctypes, wintypes, u = _win_api()
            hwnd = u.GetAncestor(wintypes.HWND(root.winfo_id()), 2) or wintypes.HWND(root.winfo_id())
            flags = SWP_NOZORDER | SWP_NOACTIVATE | (SWP_NOSIZE if w is None else SWP_NOCOPYBITS)
            u.SetWindowPos(hwnd, None, int(x), int(y), int(w or 0), int(h or 0), flags)
            return True
        except Exception:
            log_error("SetWindowPos failed:\n" + traceback.format_exc())
    if w is None:
        root.geometry(f"+{int(x)}+{int(y)}")
    else:
        root.geometry(f"{int(w)}x{int(h)}+{int(x)}+{int(y)}")
    return True


def edge_mode(px, py):
    """Какой край/угол под курсором (строка вида 'n', 'se', ...) или None."""
    if root.state() == "zoomed":
        return None
    l, t, r, b = window_rect()
    if not (l - 2 <= px <= r + 2 and t - 2 <= py <= b + 2):
        return None
    on_l, on_r = px - l < EDGE, r - px <= EDGE
    on_t, on_b = py - t < EDGE, b - py <= EDGE
    near_l, near_r = px - l < CORNER, r - px <= CORNER
    near_t, near_b = py - t < CORNER, b - py <= CORNER
    ns = "n" if on_t else "s" if on_b else ""
    we = "w" if on_l else "e" if on_r else ""
    if (on_t or on_b) and (near_l or near_r):
        we = "w" if near_l else "e"
    if (on_l or on_r) and (near_t or near_b):
        ns = "n" if near_t else "s"
    mode = ns + we
    return mode or None


def set_resize_cursor(mode):
    cur = CURSORS.get(mode, "") if mode else ""
    if cur != resize["cursor"]:
        resize["cursor"] = cur
        try:
            root.configure(cursor=cur)
        except tk.TclError:
            pass


def on_motion(e):
    if resize["start"] is None:
        set_resize_cursor(edge_mode(*cursor_pos()))


def button_down():
    """Нажата ли левая кнопка мыши (не зависит от событий Tk)."""
    try:
        import ctypes
        return bool(ctypes.windll.user32.GetAsyncKeyState(0x01) & 0x8000)
    except Exception:
        return False


def begin_freeze():
    """На время растягивания прячем сложный интерфейс (десятки виджетов Tk не успевают перерисовываться
    и дают чёрные блоки). Остаётся шапка и тёмные панели — окно меняется плавно."""
    if LIVE_CONTENT or resize.get("frozen"):
        return
    resize["frozen"] = True
    body.pack_forget()
    strip.place(x=0, y=40, width=230, relheight=1.0, height=-40)


def end_freeze():
    if not resize.get("frozen"):
        return
    resize["frozen"] = False
    strip.place_forget()
    body.pack(fill="both", expand=True)
    root.update_idletasks()


def resize_press(e):
    if resize["start"] is not None:
        return
    mode = edge_mode(*cursor_pos())
    if mode:
        resize["mode"], resize["start"], resize["last"] = mode, (cursor_pos(), window_rect()), None
        resize["job"] = root.after(8, resize_poll)


def resize_poll():
    """Растягивание опрашивает положение курсора по таймеру — так оно не зависит от потери событий
    мыши, когда содержимое окна скрыто или курсор ушёл за его пределы."""
    resize["job"] = None
    if resize["start"] is None:
        return
    if not button_down():
        finish_resize()
        return
    (cx0, cy0), (l, t, r, b) = resize["start"]
    cx, cy = cursor_pos()
    dx, dy = cx - cx0, cy - cy0
    mode = resize["mode"]
    nl, nt, nr, nb = l, t, r, b
    if "e" in mode:
        nr = max(l + MIN_W, r + dx)
    if "w" in mode:
        nl = min(r - MIN_W, l + dx)
    if "s" in mode:
        nb = max(t + MIN_H, b + dy)
    if "n" in mode:
        nt = min(b - MIN_H, t + dy)
    rect = (nl, nt, nr - nl, nb - nt)
    if rect != resize.get("last") and (dx or dy):
        begin_freeze()
        move_window(*rect)
        resize["last"] = rect
        root.update_idletasks()
    resize["job"] = root.after(8, resize_poll)


def finish_resize():
    if resize.get("job") is not None:
        root.after_cancel(resize["job"])
        resize["job"] = None
    resize["start"] = None
    end_freeze()
    set_resize_cursor(edge_mode(*cursor_pos()))


def resize_release(e):
    if resize["start"] is not None:
        finish_resize()


root.bind_all("<Motion>", on_motion, add="+")
root.bind_all("<ButtonPress-1>", resize_press, add="+")
root.bind_all("<ButtonRelease-1>", resize_release, add="+")


def drag_start(e):
    # у края окна кнопка мыши запускает растягивание, а не перетаскивание
    drag["on"] = root.state() != "zoomed" and edge_mode(*cursor_pos()) is None
    if drag["on"]:
        cx, cy = cursor_pos()
        l, t, _, _ = window_rect()
        drag.update(x=cx, y=cy, wx=l, wy=t)


def drag_move(e):
    if not drag["on"]:
        return
    cx, cy = cursor_pos()
    move_window(drag["wx"] + cx - drag["x"], drag["wy"] + cy - drag["y"])


def drag_end(e):
    drag["on"] = False


for w in (topbar, title_lbl, logo_lbl):
    w.bind("<Button-1>", drag_start)
    w.bind("<B1-Motion>", drag_move)
    w.bind("<ButtonRelease-1>", drag_end)


def remove_windows_titlebar():
    """Удаляет именно системный caption у настоящего HWND верхнего окна."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        user32.GetAncestor.restype = wintypes.HWND
        user32.GetAncestor.argtypes = [wintypes.HWND, ctypes.c_uint]
        user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
        user32.GetWindowLongW.restype = ctypes.c_long
        user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
        user32.SetWindowLongW.restype = ctypes.c_long
        user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int,
                                        ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
        root.update_idletasks()
        child_hwnd = wintypes.HWND(root.winfo_id())
        GA_ROOT = 2
        hwnd = user32.GetAncestor(child_hwnd, GA_ROOT)
        if not hwnd:
            hwnd = child_hwnd
        GWL_STYLE = -16
        WS_CAPTION, WS_THICKFRAME, WS_BORDER, WS_DLGFRAME = 0x00C00000, 0x00040000, 0x00800000, 0x00400000
        style = user32.GetWindowLongW(hwnd, GWL_STYLE)
        user32.SetWindowLongW(hwnd, GWL_STYLE, style & ~(WS_CAPTION | WS_THICKFRAME | WS_BORDER | WS_DLGFRAME))
        GWL_EXSTYLE, WS_EX_WINDOWEDGE, WS_EX_CLIENTEDGE = -20, 0x00000100, 0x00000200
        exstyle = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, exstyle & ~(WS_EX_WINDOWEDGE | WS_EX_CLIENTEDGE))
        SWP_NOSIZE, SWP_NOMOVE, SWP_NOZORDER, SWP_FRAMECHANGED = 0x0001, 0x0002, 0x0004, 0x0020
        user32.SetWindowPos(hwnd, None, 0, 0, 0, 0,
                            SWP_NOSIZE | SWP_NOMOVE | SWP_NOZORDER | SWP_FRAMECHANGED)
        try:
            dwmapi = ctypes.windll.dwmapi
            DWMWA_BORDER_COLOR = 34
            DWMWA_COLOR_NONE = ctypes.c_int(0xFFFFFFFE)
            dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_BORDER_COLOR,
                                         ctypes.byref(DWMWA_COLOR_NONE), ctypes.sizeof(DWMWA_COLOR_NONE))
        except Exception:
            pass
        root.configure(highlightthickness=0, bd=0, relief="flat")
    except Exception:
        log_error("Borderless window setup failed:\n" + traceback.format_exc())


root.after(250, remove_windows_titlebar)
root.bind("<Map>", lambda e: root.after(80, remove_windows_titlebar))


body = TH(tk.Frame(root), bg="BG")
body.pack(fill="both", expand=True)
sidebar = TH(tk.Frame(body, width=230), bg="SIDE")
sidebar.pack(side="left", fill="y")
sidebar.pack_propagate(False)
strip = TH(tk.Frame(root), bg="SIDE")   # заглушка под сайдбар на время растягивания окна
content = TH(tk.Frame(body), bg="BG")
content.pack(side="left", fill="both", expand=True, padx=28, pady=(14, 20))

pages, nav = {}, {}


def show(name):
    for n, p in pages.items():
        p.pack_forget()
        nav[n].set_active(n == name)
    pages[name].pack(fill="both", expand=True)


# ---------------- иконки навигации ----------------
ICON_PX = 22
_icon_cache = {}


def nav_icon(name, tt, angle, color):
    spins = name in ("settings", "antiban", "team")
    key = (name, 0 if spins else round(tt * 20), angle if spins else 0, color)
    img = _icon_cache.get(key)
    if img is None:
        if name == "overview":
            pil = icon_stack(ICON_PX, tt, color)
        elif name == "settings":
            pil = icon_gear(ICON_PX, angle, color)
        elif name == "antiban":
            pil = icon_shield(ICON_PX, angle, color)
        elif name == "team":
            pil = icon_eye(ICON_PX, angle, color)
        else:
            pil = icon_link(ICON_PX, tt, color)
        img = ImageTk.PhotoImage(pil)
        _icon_cache[key] = img
    return img


class NavItem(tk.Frame):
    """Пункт меню с анимированной иконкой (анимация при наведении)."""

    def __init__(self, parent, name, key):
        super().__init__(parent, cursor="hand2")
        self.name, self.active, self.hover = name, False, False
        self.t, self.angle, self._job = 0.0, 0, None
        self.icon = tk.Label(self, bd=0, highlightthickness=0, cursor="hand2")
        self.icon.pack(side="left", padx=(14, 10), pady=11)
        self.text = tk.Label(self, font=(FONT, 9, "bold"), anchor="w", cursor="hand2")
        L(self.text, key)
        self.text.pack(side="left", fill="x", expand=True)
        for w in (self, self.icon, self.text):
            w.bind("<Enter>", lambda e: self._set_hover(True))
            w.bind("<Leave>", lambda e: self.after(20, self._recheck))
            w.bind("<Button-1>", lambda e: show(self.name))
        custom_widgets.append(self)
        self.restyle()

    def _recheck(self):
        try:
            x, y = self.winfo_pointerxy()
            w = self.winfo_containing(x, y)
        except (tk.TclError, KeyError):
            w = None
        inside = w is not None and (w is self or str(w).startswith(str(self) + "."))
        self._set_hover(inside)

    def _set_hover(self, v):
        if v != self.hover:
            self.hover = v
            self.restyle()
            self._kick()

    def set_active(self, v):
        self.active = v
        self.restyle()

    def _icon_color(self):
        return ACT_FG if self.active else lerp_hex(P["MUT"], P["TXT"], self.t)

    def draw_icon(self):
        img = nav_icon(self.name, self.t, self.angle, self._icon_color())
        self.icon.configure(image=img)
        self.icon.image = img

    def restyle(self):
        bg = P["ACC"] if self.active else (P["BTN"] if self.hover else P["SIDE"])
        fg = ACT_FG if self.active else (P["TXT"] if self.hover else P["MUT"])
        self.configure(bg=bg)
        self.icon.configure(bg=bg)
        self.text.configure(bg=bg, fg=fg)
        self.draw_icon()

    def _kick(self):
        if self._job is None:
            self._job = self.after(16, self._tick)

    def _tick(self):
        self._job = None
        target = 1.0 if self.hover else 0.0
        self.t += (target - self.t) * 0.3
        if abs(target - self.t) < 0.02:
            self.t = target
        busy = self.t != target
        spin = {"settings": (5, 45), "antiban": (10, 360), "team": (10, 360)}.get(self.name)
        if spin and (self.hover or self.angle % spin[1] != 0):
            # шестерёнка крутится, щит пульсирует, пока курсор на пункте; потом докручиваются до исходного вида
            self.angle = (self.angle + spin[0]) % 360
            busy = True
        self.draw_icon()
        if busy:
            self._job = self.after(20, self._tick)


for n, key in (("overview", "nav_overview"), ("settings", "nav_settings"), ("antiban", "nav_antiban"),
               ("team", "nav_team"), ("interface", "nav_interface")):
    item = NavItem(sidebar, n, key)
    item.pack(fill="x", pady=(20 if n == "overview" else 6, 0), padx=12)
    nav[n] = item


class SmoothText(tk.Label):
    """Гладкая (не пиксельная) надпись; с url — кликабельная ссылка с подчёркиванием при наведении."""

    def __init__(self, parent, text=None, key=None, px=13, fg="MUT", bold=False, url=None, on_hover=None):
        super().__init__(parent, bd=0, highlightthickness=0, padx=0, pady=0)
        self.text_, self.key, self.px, self.fg, self.bold, self.url = text, key, px, fg, bold, url
        self.hover, self.on_hover = False, on_hover
        if url:
            self.configure(cursor="hand2")
            self.bind("<Enter>", lambda e: self._hover(True))
            self.bind("<Leave>", lambda e: self._hover(False))
            self.bind("<Button-1>", lambda e: self.open())
        custom_widgets.append(self)
        self.restyle()

    def open(self):
        try:
            webbrowser.open(self.url)
        except Exception:
            log_error("Could not open link:\n" + traceback.format_exc())

    def _hover(self, v):
        self.hover = v
        self.restyle()
        if self.on_hover:
            self.on_hover(v)

    def restyle(self):
        text = t(self.key) if self.key else self.text_
        color = P["TXT"] if (self.url and self.hover) else P[self.fg]
        pil = render_text(text, self.px, color, bold=self.bold)
        if pil is not None:
            self.photo = ImageTk.PhotoImage(pil)
            self.configure(image=self.photo, text="", bg=P["SIDE"])
        else:
            self.configure(image="", text=text, font=(FONT, int(self.px * 0.75), "bold" if self.bold else "normal"),
                           fg=color, bg=P["SIDE"])


# нижний блок сайдбара. Сверху вниз: «by outmoney», версия, название. Все строки с одним левым краем.
SmoothText(sidebar, text="PIRATE TOKEN BOT", px=12, fg="MUT", bold=True) \
    .pack(side="bottom", anchor="w", padx=18, pady=(0, 18))
SmoothText(sidebar, key="version", px=13, fg="MUT").pack(side="bottom", anchor="w", padx=18, pady=(0, 8))
class FadeTip(tk.Label):
    """Маленькая подсказка, которая плавно появляется (проявление + выезд снизу) при наведении."""
    RISE = 5   # px выезда

    def __init__(self, parent, key, px=11):
        super().__init__(parent, bd=0, highlightthickness=0, padx=0, pady=0)
        self.key, self.px, self.p, self.target, self._job = key, px, 0.0, 0.0, None
        custom_widgets.append(self)
        self.restyle()

    def show(self, v):
        self.target = 1.0 if v else 0.0
        if self._job is None:
            self._job = self.after(16, self._tick)

    def _tick(self):
        self._job = None
        self.p += (self.target - self.p) * 0.28
        if abs(self.target - self.p) < 0.03:
            self.p = self.target
        self.restyle()
        if self.p != self.target:
            self._job = self.after(16, self._tick)

    def restyle(self):
        color = lerp_hex(P["SIDE"], P["MUT"], self.p)
        pil = render_text(t(self.key), self.px, color, bold=False, slide=(1 - self.p) * self.RISE)
        if pil is not None:
            self.photo = ImageTk.PhotoImage(pil)
            self.configure(image=self.photo, text="", bg=P["SIDE"])
        else:
            self.configure(image="", text=t(self.key) if self.p > 0.5 else "", font=(FONT, 8),
                           fg=P["MUT"], bg=P["SIDE"])


by_row = TH(tk.Frame(sidebar), bg="SIDE")
by_row.pack(side="bottom", anchor="w", padx=18, pady=(0, 6))
tg_tip = FadeTip(by_row, "tg_channel")
tg_tip.grid(row=0, column=1, sticky="w")
SmoothText(by_row, text="by", px=14, fg="MUT").grid(row=1, column=0, sticky="w")    # «by» — обычный текст
SmoothText(by_row, text="outmoney", px=14, fg="ACC_H", bold=True, url=TELEGRAM_URL,
           on_hover=tg_tip.show).grid(row=1, column=1, sticky="w", padx=(3, 0))


# ---------------- вспомогательные виджеты ----------------
def mk(parent, key=None, bg="CARD", fg="MUT", font=(FONT, 9), **kw):
    w = tk.Label(parent, font=font, **kw)
    TH(w, bg=bg, fg=fg)
    if key:
        L(w, key)
    return w


def header(parent, title_key, sub_key):
    mk(parent, title_key, bg="BG", fg="TXT", font=(FONT, 22, "bold")).pack(anchor="w")
    mk(parent, sub_key, bg="BG", fg="MUT", font=(FONT, 9)).pack(anchor="w", pady=(0, 14))


def card(parent, **kw):
    return TH(tk.Frame(parent, padx=16, pady=12, **kw), bg="CARD")


def lbl(parent, key, **kw):
    return mk(parent, key, bg="CARD", fg="MUT", font=(FONT, 9), **kw)


hover_fx = []   # все кнопки с плавной подсветкой (перекрашиваются при смене темы)


def _col_of(v):
    """Цвет из роли палитры, hex-строки или функции."""
    return v() if callable(v) else (v if v.startswith("#") else P[v])


class HoverFx:
    """Плавная подсветка кнопки при наведении курсора (цвет фона и, по желанию, текста)."""

    def __init__(self, widget, base, hover, fg=None, hover_fg=None, group=None):
        self.w, self.base, self.hover, self.fg, self.hover_fg = widget, base, hover, fg, hover_fg
        self.group = tuple(group) if group else (widget,)
        self.p, self.target, self._job = 0.0, 0.0, None
        for g in self.group:
            g.bind("<Enter>", lambda e: self.go(1.0), add="+")
            g.bind("<Leave>", lambda e: self.w.after(25, self._recheck), add="+")
        hover_fx.append(self)
        self.apply()

    def _recheck(self):
        try:
            x, y = self.w.winfo_pointerxy()
            under = self.w.winfo_containing(x, y)
        except (tk.TclError, KeyError):
            under = None
        inside = under is not None and any(under is g or str(under).startswith(str(g) + ".") for g in self.group)
        self.go(1.0 if inside else 0.0)

    def go(self, target):
        self.target = target
        if self._job is None:
            self._job = self.w.after(16, self._tick)

    def _tick(self):
        self._job = None
        self.p += (self.target - self.p) * 0.35
        if abs(self.target - self.p) < 0.03:
            self.p = self.target
        self.apply()
        if self.p != self.target:
            self._job = self.w.after(16, self._tick)

    def apply(self):
        try:
            opts = {"bg": lerp_hex(_col_of(self.base), _col_of(self.hover), self.p)}
            if self.fg:
                opts["fg"] = lerp_hex(_col_of(self.fg), _col_of(self.hover_fg or self.fg), self.p)
            self.w.configure(**opts)
        except tk.TclError:
            pass


class Spin(tk.Frame):
    """Поле с красивыми стрелками вверх/вниз."""

    def __init__(self, parent, var, lo, hi, inc, w=6):
        super().__init__(parent, highlightthickness=1)
        TH(self, bg="FIELD", highlightbackground="LINE", highlightcolor="ACC")
        self.var, self.lo, self.hi, self.inc = var, lo, hi, inc
        self.entry = tk.Entry(self, textvariable=var, width=w, relief="flat", bd=0, font=(FONT, 10),
                              highlightthickness=0)
        TH(self.entry, bg="FIELD", fg="TXT", insertbackground="TXT")
        self.entry.pack(side="left", padx=(8, 4), pady=5)
        arrows = TH(tk.Frame(self), bg="FIELD")
        arrows.pack(side="right", fill="y")
        for sym, d in (("▲", 1), ("▼", -1)):
            a = tk.Label(arrows, text=sym, font=(FONT, 6), width=3, cursor="hand2")
            TH(a, bg="BTN", fg="MUT")
            a.pack(fill="both", expand=True, pady=(0 if d == 1 else 1, 0))
            a.bind("<Button-1>", lambda e, d=d: self.step(d))
            a.bind("<Enter>", lambda e, a=a: a.config(bg=P["ACC"], fg=ACT_FG))
            a.bind("<Leave>", lambda e, a=a: a.config(bg=P["BTN"], fg=P["MUT"]))
        self.entry.bind("<MouseWheel>", lambda e: self.step(1 if e.delta > 0 else -1))
        self.entry.bind("<FocusIn>", lambda e: self.config(highlightbackground=P["ACC"]))
        self.entry.bind("<FocusOut>", lambda e: self.config(highlightbackground=P["LINE"]))

    def step(self, d):
        try:
            v = float(self.var.get().replace(",", "."))
        except ValueError:
            v = self.lo
        v = min(self.hi, max(self.lo, v + d * self.inc))
        self.var.set(str(num(round(v, 2))))


class Dropdown(tk.Frame):
    """Тёмный выпадающий список. В var хранится внутреннее значение, а показывается перевод."""

    def __init__(self, parent, var, values, label_fn=lambda v: v):
        super().__init__(parent, highlightthickness=1, cursor="hand2")
        TH(self, bg="FIELD", highlightbackground="LINE")
        self.var, self.values, self.label_fn = var, values, label_fn
        self.disp = tk.StringVar()
        self.lbl = tk.Label(self, textvariable=self.disp, font=(FONT, 10), width=12, anchor="w")
        TH(self.lbl, bg="FIELD", fg="TXT")
        self.lbl.pack(side="left", padx=(8, 0), pady=5)
        self.arrow = tk.Label(self, text="▼", font=(FONT, 7), width=3)
        TH(self.arrow, bg="BTN", fg="MUT")
        HoverFx(self.arrow, "BTN", "ACC", "MUT", ACT_FG, group=(self, self.lbl, self.arrow))
        self.arrow.pack(side="right", fill="y")
        self.menu = tk.Menu(self, tearoff=0, bd=0, relief="flat", font=(FONT, 10))
        TH(self.menu, bg="FIELD", fg="TXT", activebackground="ACC", activeforeground=ACT_FG)
        dropdown_instances.append(self)
        self.rebuild()
        var.trace_add("write", lambda *a: self.disp.set(self.label_fn(var.get())))
        for w in (self, self.lbl, self.arrow):
            w.bind("<Button-1>", self.open)

    def rebuild(self):
        self.menu.delete(0, "end")
        for v in self.values:
            self.menu.add_command(label=self.label_fn(v), command=lambda v=v: self.var.set(v))
        self.disp.set(self.label_fn(self.var.get()))

    def open(self, e=None):
        self.menu.tk_popup(self.winfo_rootx(), self.winfo_rooty() + self.winfo_height())


class Check(tk.Frame):
    """Свой чекбокс: скруглённый квадрат в цветах темы с анимированной галочкой."""

    def __init__(self, parent, var, key, command=None):
        super().__init__(parent)
        TH(self, bg="CARD")
        self.var, self.command, self.hover, self._job = var, command, False, None
        self.p = 1.0 if var.get() else 0.0
        self.box = tk.Label(self, bd=0, highlightthickness=0, cursor="hand2")
        TH(self.box, bg="CARD")
        self.box.pack(side="left")
        self.txt = tk.Label(self, font=(FONT, 9), cursor="hand2")
        TH(self.txt, bg="CARD", fg="TXT")
        L(self.txt, key)
        self.txt.pack(side="left", padx=(10, 0))
        for w in (self, self.box, self.txt):
            w.bind("<Button-1>", self.toggle)
            w.bind("<Enter>", lambda e: self._set_hover(True))
            w.bind("<Leave>", lambda e: self._set_hover(False))
        var.trace_add("write", lambda *a: self._kick())
        custom_widgets.append(self)
        self.restyle()

    def _set_hover(self, v):
        self.hover = v
        self.restyle()

    def toggle(self, e=None):
        self.var.set(not self.var.get())
        if self.command:
            self.command()

    def restyle(self):
        pil = render_check(18, self.p, self.hover, P["LINE"], P["ACC"], P["FIELD"], ACT_FG)
        self.img = ImageTk.PhotoImage(pil)
        self.box.configure(image=self.img)

    def _kick(self):
        if self._job is None:
            self._job = self.after(16, self._tick)

    def _tick(self):
        self._job = None
        target = 1.0 if self.var.get() else 0.0
        step = 0.2
        self.p = min(target, self.p + step) if target > self.p else max(target, self.p - step)
        self.restyle()
        if self.p != target:
            self._job = self.after(16, self._tick)


# ---- Центр управления (бывший Overview) ----
ov = TH(tk.Frame(content), bg="BG")
pages["overview"] = ov
header(ov, "cc_title", "cc_sub")

status_card = card(ov)
status_card.pack(fill="x")
left = TH(tk.Frame(status_card), bg="CARD")
left.pack(side="left", fill="x", expand=True)
mk(left, "sys_status", font=(FONT, 8, "bold")).pack(anchor="w")
row = TH(tk.Frame(left), bg="CARD")
row.pack(anchor="w", pady=(6, 2))
dot = TH(tk.Label(row, text="●", font=(FONT, 12)), bg="CARD")
dot.pack(side="left")
status_var = tk.StringVar(value=t("ph_stopped"))
mk(row, textvariable=status_var, fg="TXT", font=(FONT, 16, "bold")).pack(side="left", padx=8)
sub_var = tk.StringVar(value=t("sub_ready"))
mk(left, textvariable=sub_var).pack(anchor="w")
right = TH(tk.Frame(status_card), bg="CARD")
right.pack(side="right")
mk(right, "next_cycle", font=(FONT, 8, "bold")).pack(anchor="e")
next_var = tk.StringVar(value="01:00")
mk(right, textvariable=next_var, fg="TXT", font=(FONT, 24, "bold")).pack(anchor="e", pady=(6, 0))

stats = TH(tk.Frame(ov), bg="BG")
stats.pack(fill="x", pady=16)
match_var, lobby_var, rounds_var = tk.StringVar(), tk.StringVar(), tk.StringVar(value="0")
for i, (k, v) in enumerate((("match_duration", match_var), ("lobby_delay", lobby_var), ("completed", rounds_var))):
    c = card(stats)
    c.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 8, 0))
    stats.columnconfigure(i, weight=1, uniform="s")
    mk(c, k, font=(FONT, 8, "bold")).pack(anchor="w")
    mk(c, textvariable=v, fg="TXT", font=(FONT, 16, "bold")).pack(anchor="w", pady=(8, 0))

start_btn = tk.Button(ov, text=t("start_queue"), fg=ACT_FG, activeforeground=ACT_FG,
                      relief="flat", bd=0, font=(FONT, 11, "bold"), pady=14, cursor="hand2", command=toggle)
start_btn.pack(fill="x")
start_fx = HoverFx(start_btn, lambda: P["RED"] if state["running"] else P["ACC"],
                   lambda: P["RED_H"] if state["running"] else P["ACC_H"])
hint_var = tk.StringVar()
mk(ov, textvariable=hint_var, bg="BG", font=(FONT, 8)).pack(pady=10)

# ---- Настройки ----
st = TH(tk.Frame(content), bg="BG")
pages["settings"] = st
header(st, "settings_title", "settings_sub")

timing = card(st)
timing.pack(fill="x")
mk(timing, "timing", fg="TXT", font=(FONT, 9, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 8))
match_v = tk.StringVar(value=str(num(cfg["match_min"])))
lobby_v = tk.StringVar(value=str(num(cfg["lobby_sec"])))
key_v = tk.StringVar(value=cfg["hotkey"])
lbl(timing, "match_min_lbl").grid(row=1, column=0, sticky="w", pady=5)
Spin(timing, match_v, 0.1, 180, 1).grid(row=1, column=1, padx=14)
lbl(timing, "lobby_sec_lbl").grid(row=2, column=0, sticky="w", pady=5)
Spin(timing, lobby_v, 1, 600, 1).grid(row=2, column=1, padx=14)
lbl(timing, "hotkey_lbl").grid(row=2, column=2, sticky="w", padx=(30, 0))
key_btn = tk.Button(timing, relief="flat", bd=0, font=(FONT, 9, "bold"), padx=12, pady=7, cursor="hand2")
TH(key_btn, bg="BTN", fg="TXT", activebackground="ACC", activeforeground=ACT_FG)
HoverFx(key_btn, "BTN", "HOVER")
key_btn.grid(row=2, column=3, padx=10)
survey_v = tk.BooleanVar(value=bool(cfg.get("auto_skip_survey", True)))
Check(timing, survey_v, "survey_auto",
      command=lambda: persist_preference("auto_skip_survey", bool(survey_v.get()))).grid(
    row=3, column=0, columnspan=4, sticky="w", pady=(10, 0))
capture_hook = None
capture_active = False

# ---- Интерфейс ----
ui_page = TH(tk.Frame(content), bg="BG")
pages["interface"] = ui_page
header(ui_page, "ui_title", "ui_sub")
appearance = card(ui_page)
appearance.pack(fill="x")
mk(appearance, "appearance", fg="TXT", font=(FONT, 9, "bold")).grid(
    row=0, column=0, sticky="w", pady=(0, 8), columnspan=4)
theme_v = tk.StringVar(value=cfg["theme"])
language_v = tk.StringVar(value=cfg["language"])
lbl(appearance, "theme").grid(row=1, column=0, sticky="w", pady=5)
Dropdown(appearance, theme_v, ["Purple", "Black", "White"], lambda v: t("theme_" + v)).grid(
    row=1, column=1, padx=14, sticky="w")
lbl(appearance, "language").grid(row=1, column=2, sticky="w", padx=(24, 0))
Dropdown(appearance, language_v, LANGS).grid(row=1, column=3, padx=10, sticky="w")
sound_v = tk.StringVar(value=cfg["sound"])
lbl(appearance, "sound_lbl").grid(row=2, column=0, sticky="w", pady=(12, 5))
Dropdown(appearance, sound_v, [f"Sound {i}" for i in range(1, 10)],
         lambda v: t("sound_n", v.split()[-1])).grid(row=2, column=1, padx=14, sticky="w")
sound_enabled_v = tk.BooleanVar(value=bool(cfg.get("sound_enabled", True)))
Check(appearance, sound_enabled_v, "sound_on",
      command=lambda: persist_preference("sound_enabled", bool(sound_enabled_v.get()))).grid(
    row=2, column=2, columnspan=2, sticky="w", padx=(24, 0), pady=(12, 5))

coords = card(st)
coords.pack(fill="x", pady=14)
mk(coords, "coords", fg="TXT", font=(FONT, 9, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 8))
cvars = {}
layout = (("play", "play", 1, 0), ("leave", "leave", 1, 4), ("confirm", "confirm", 2, 0), ("rmb", "rclick", 2, 4))
for key, name, r, c0 in layout:
    xv, yv = tk.StringVar(value=str(cfg[key][0])), tk.StringVar(value=str(cfg[key][1]))
    cvars[key] = (xv, yv)
    lbl(coords, name).grid(row=r, column=c0, sticky="w", pady=5, padx=(0 if c0 == 0 else 30, 0))
    Spin(coords, xv, 0, 7680, 1, 5).grid(row=r, column=c0 + 1, padx=6)
    Spin(coords, yv, 0, 4320, 1, 5).grid(row=r, column=c0 + 2, padx=6)

note_state = ("note_default", ())
note_var = tk.StringVar()


def set_note(key, *args):
    global note_state
    note_state = (key, args)
    note_var.set(t(key, *args))


# ---- Антибан ----
ab_page = TH(tk.Frame(content), bg="BG")
pages["antiban"] = ab_page
header(ab_page, "ab_title", "ab_sub")

ab_keys_card = card(ab_page)
ab_keys_card.pack(fill="x")
ab_enabled_v = tk.BooleanVar(value=bool(cfg.get("ab_enabled", False)))
Check(ab_keys_card, ab_enabled_v, "ab_enable",
      command=lambda: persist_preference("ab_enabled", bool(ab_enabled_v.get()))).grid(
    row=0, column=0, columnspan=4, sticky="w", pady=(0, 10))
mk(ab_keys_card, "ab_keys", fg="TXT", font=(FONT, 9, "bold")).grid(row=1, column=0, columnspan=4, sticky="w", pady=(0, 6))
ab_key_vars = {}


def ab_key_changed(k):
    cfg["ab_keys"][k] = bool(ab_key_vars[k].get())
    persist_preference("ab_keys", cfg["ab_keys"])


for idx, k in enumerate(AB_BASE):
    ab_key_vars[k] = tk.BooleanVar(value=bool(cfg["ab_keys"].get(k, True)))
    Check(ab_keys_card, ab_key_vars[k], "key_" + k, command=lambda k=k: ab_key_changed(k)).grid(
        row=2 + idx // 4, column=idx % 4, sticky="w", padx=(0, 28), pady=4)

ab_key_vars["custom"] = tk.BooleanVar(value=bool(cfg["ab_keys"].get("custom", False)))
Check(ab_keys_card, ab_key_vars["custom"], "key_custom", command=lambda: ab_key_changed("custom")).grid(
    row=4, column=0, sticky="w", padx=(0, 28), pady=4)
custom_btn = tk.Button(ab_keys_card, relief="flat", bd=0, font=(FONT, 9, "bold"), padx=12, pady=5, cursor="hand2",
                       command=lambda: start_capture(custom_btn, set_custom_key))
TH(custom_btn, bg="BTN", fg="TXT", activebackground="ACC", activeforeground=ACT_FG)
HoverFx(custom_btn, "BTN", "HOVER")
custom_btn.grid(row=4, column=1, columnspan=2, sticky="w", pady=4)

ab_time_card = card(ab_page)
ab_time_card.pack(fill="x", pady=(14, 10))
mk(ab_time_card, "ab_timing", fg="TXT", font=(FONT, 9, "bold")).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 6))
ab_pmin_v, ab_pmax_v = tk.StringVar(value=str(num(cfg["ab_pmin"]))), tk.StringVar(value=str(num(cfg["ab_pmax"])))
ab_amax_v, ab_delay_v = tk.StringVar(value=str(num(cfg["ab_amax"]))), tk.StringVar(value=str(num(cfg["ab_delay"])))
for key, var, lo, hi, inc, row, col in (("ab_pmin_lbl", ab_pmin_v, 0.05, 60, 0.1, 1, 0),
                                        ("ab_pmax_lbl", ab_pmax_v, 0.05, 120, 0.1, 1, 2),
                                        ("ab_amax_lbl", ab_amax_v, 0.3, 30, 0.1, 2, 0),
                                        ("ab_delay_lbl", ab_delay_v, 0, 600, 5, 2, 2)):
    lbl(ab_time_card, key).grid(row=row, column=col, sticky="w", pady=4, padx=(24 if col else 0, 0))
    Spin(ab_time_card, var, lo, hi, inc).grid(row=row, column=col + 1, padx=10, sticky="w")

ab_pixel_on_v = tk.BooleanVar(value=bool(cfg.get("ab_pixel_on", False)))
Check(ab_time_card, ab_pixel_on_v, "ab_pixel_on",
      command=lambda: persist_preference("ab_pixel_on", bool(ab_pixel_on_v.get()))).grid(
    row=3, column=0, columnspan=2, sticky="w", pady=(8, 2))
marker_box = TH(tk.Frame(ab_time_card), bg="CARD")
marker_sw = tk.Label(marker_box, width=3, bd=0)
marker_sw.pack(side="left")
marker_info = tk.StringVar()
mk(marker_box, textvariable=marker_info, fg="TXT", font=(FONT, 9)).pack(side="left", padx=8)
marker_box.grid(row=3, column=2, columnspan=2, sticky="w", pady=(8, 2), padx=(24, 0))
mk(ab_time_card, "ab_marker_hint", font=(FONT, 8), wraplength=600, justify="left").grid(
    row=4, column=0, columnspan=4, sticky="w", pady=(2, 0))
ab_save_b = tk.Button(ab_page, relief="flat", bd=0, font=(FONT, 10, "bold"), pady=12, cursor="hand2",
                      command=lambda: save_settings(antiban_only=True))
TH(ab_save_b, bg="ACC", fg=ACT_FG, activebackground="ACC_H", activeforeground=ACT_FG)
HoverFx(ab_save_b, "ACC", "ACC_H")
L(ab_save_b, "ab_save")
ab_save_b.pack(fill="x")

btns = TH(tk.Frame(st), bg="BG")
btns.pack(fill="x")
hk_handle = None


capture_target = None   # кнопка, для которой сейчас ждём нажатие клавиши


def start_capture(button, apply):
    """Ждёт нажатие любой клавиши и передаёт её имя в apply(name)."""
    global capture_hook, capture_active, capture_target
    if capture_active:
        return
    capture_active, capture_target = True, button
    button.config(state="disabled")

    def on_key(event):
        global capture_hook, capture_active, capture_target
        if event.event_type != "down":
            return
        name = (event.name or "").lower().strip()
        aliases = {"left ctrl": "ctrl", "right ctrl": "ctrl", "left shift": "shift",
                   "right shift": "shift", "left alt": "alt", "right alt": "alt",
                   "left windows": "windows", "right windows": "windows"}
        name = aliases.get(name, name)
        if not name or name in ("unknown", ""):
            return
        try:
            keyboard.unhook(capture_hook)
        except Exception:
            pass
        capture_hook = None

        def finish_capture():
            global capture_active, capture_target
            capture_active, capture_target = False, None
            button.config(state="normal")
            apply(name)
        root.after(0, finish_capture)

    try:
        capture_hook = keyboard.on_press(on_key, suppress=False)
    except Exception as e:
        capture_active, capture_target = False, None
        button.config(state="normal")
        set_note("note_cap_err", str(e))


def set_hotkey(name):
    key_v.set(name)
    cfg["hotkey"] = name
    bind_hotkey()
    persist_preference("hotkey", name)
    set_note("note_hotkey", name.upper())


def set_custom_key(name):
    cfg["ab_custom_key"] = name
    persist_preference("ab_custom_key", name)
    set_note("note_custom_key", name.upper())


key_btn.config(command=lambda: start_capture(key_btn, set_hotkey))


VK_NAMES = {"space": 0x20, "enter": 0x0D, "tab": 0x09, "esc": 0x1B, "escape": 0x1B, "shift": 0x10, "ctrl": 0x11,
            "alt": 0x12, "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27, "home": 0x24, "end": 0x23,
            "page up": 0x21, "page down": 0x22, "insert": 0x2D, "delete": 0x2E, "caps lock": 0x14,
            "backspace": 0x08, "windows": 0x5B, "print screen": 0x2C, "scroll lock": 0x91, "pause": 0x13,
            "num lock": 0x90}


def vk_code(name):
    """Виртуальный код клавиши Windows по её имени (или None)."""
    name = (name or "").lower().strip()
    if name in VK_NAMES:
        return VK_NAMES[name]
    if len(name) >= 2 and name[0] == "f" and name[1:].isdigit() and 1 <= int(name[1:]) <= 24:
        return 0x70 + int(name[1:]) - 1
    if len(name) == 1:
        try:
            v = ctypes.windll.user32.VkKeyScanW(ord(name))
            return v & 0xFF if v != -1 else None
        except Exception:
            return None
    return None


hotkey_vk = [None]      # код клавиши старт/стоп для опроса
_last_fire = [0.0]


def fire_hotkey():
    """Нажатие клавиши старт/стоп. Хук и опрос могут сработать оба — дубль отсекаем по времени."""
    now = time.time()
    if now - _last_fire[0] < 0.4:
        return
    _last_fire[0] = now
    root.after(0, toggle)


def hotkey_poll_loop():
    """Опрашивает состояние клавиши напрямую у Windows. Работает, даже если хук клавиатуры не сработал
    (игра от администратора, «залипшая» клавиша в библиотеке keyboard, снятый системой хук)."""
    prev = False
    try:
        gas = ctypes.windll.user32.GetAsyncKeyState
    except Exception:
        return
    while not quitting:
        vk = hotkey_vk[0]
        if vk:
            down = bool(gas(vk) & 0x8000)
            if down and not prev and not capture_active:
                fire_hotkey()
            prev = down
        else:
            prev = False
        time.sleep(0.015)


def bind_hotkey():
    global hk_handle
    if hk_handle is not None:
        try:
            keyboard.remove_hotkey(hk_handle)
        except Exception:
            pass
        hk_handle = None
    hotkey_vk[0] = vk_code(cfg["hotkey"])
    try:
        hk_handle = keyboard.add_hotkey(cfg["hotkey"].lower(), fire_hotkey)
    except Exception as e:
        log_error(traceback.format_exc())
        if hotkey_vk[0] is None:      # ни хука, ни опроса — сообщаем об ошибке
            set_note("note_hk_err", str(e))


def refresh_labels():
    match_var.set(fmt(cfg["match_min"] * 60))
    lobby_var.set(fmt(cfg["lobby_sec"]))


# ---------------- применение темы и языка ----------------
def apply_theme(theme_name):
    P.clear()
    P.update(THEMES.get(theme_name, THEMES["Purple"]))
    for widget, roles in _themed:
        try:
            widget.configure(**{opt: _col(role) for opt, role in roles.items()})
        except tk.TclError:
            pass
    for fx in hover_fx:
        fx.apply()
    _icon_cache.clear()
    for obj in custom_widgets:
        obj.restyle()
    root.configure(bg=P["BG"])
    apply_app_icon(theme_name)


def apply_language():
    for widget, key, args in _i18n:
        try:
            widget.configure(text=t(key, *args))
        except tk.TclError:
            pass
    for dd in dropdown_instances:
        dd.rebuild()
    for obj in custom_widgets:
        obj.restyle()
    set_note(*((note_state[0],) + tuple(note_state[1])))


def persist_preference(key, value):
    cfg[key] = value
    try:
        with open(CFG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        log_error("Could not save preference:\n" + traceback.format_exc())


def on_theme_selected(*_):
    selected = theme_v.get()
    cfg["theme"] = selected
    apply_theme(selected)
    persist_preference("theme", selected)


def on_language_selected(*_):
    selected = language_v.get()
    cfg["language"] = selected
    persist_preference("language", selected)
    root.after(10, apply_language)   # после закрытия меню, чтобы не перестраивать его на лету


theme_v.trace_add("write", on_theme_selected)
language_v.trace_add("write", on_language_selected)


def on_sound_selected(*_):
    persist_preference("sound", sound_v.get())
    play_toggle_sound()   # предпрослушивание


sound_v.trace_add("write", on_sound_selected)


def save_settings(antiban_only=False):
    try:
        ab_vals = {"ab_pmin": num(ab_pmin_v.get().replace(",", ".")), "ab_pmax": num(ab_pmax_v.get().replace(",", ".")),
                   "ab_amax": num(ab_amax_v.get().replace(",", ".")), "ab_delay": num(ab_delay_v.get().replace(",", "."))}
    except ValueError:
        set_note("note_numbers")
        return
    if ab_vals["ab_pmin"] > ab_vals["ab_pmax"]:
        set_note("note_ab_range")
        return
    cfg.update(ab_vals)
    cfg["ab_pixel_on"] = bool(ab_pixel_on_v.get())
    cfg["ab_enabled"] = bool(ab_enabled_v.get())
    cfg["ab_keys"] = {k: bool(v.get()) for k, v in ab_key_vars.items()}
    if antiban_only:
        persist_preference("ab_enabled", cfg["ab_enabled"])
        set_note("note_ab_saved")
        return
    try:
        cfg["match_min"] = num(match_v.get().replace(",", "."))
        cfg["lobby_sec"] = num(lobby_v.get().replace(",", "."))
        for k, (xv, yv) in cvars.items():
            cfg[k] = [int(float(xv.get())), int(float(yv.get()))]
    except ValueError:
        set_note("note_numbers")
        return
    cfg["hotkey"] = key_v.get()
    cfg["theme"] = theme_v.get()
    cfg["language"] = language_v.get()
    cfg["sound"] = sound_v.get()
    cfg["sound_enabled"] = bool(sound_enabled_v.get())
    with open(CFG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    bind_hotkey()
    refresh_labels()
    set_note("note_saved")


def reset_defaults():
    match_v.set(str(DEFAULTS["match_min"]))
    lobby_v.set(str(DEFAULTS["lobby_sec"]))
    key_v.set(DEFAULTS["hotkey"])
    theme_v.set(DEFAULTS["theme"])
    language_v.set(DEFAULTS["language"])
    sound_v.set(DEFAULTS["sound"])
    sound_enabled_v.set(DEFAULTS["sound_enabled"])
    ab_enabled_v.set(DEFAULTS["ab_enabled"])
    td_enabled_v.set(DEFAULTS["td_enabled"])
    survey_v.set(DEFAULTS["auto_skip_survey"])
    td_clear()
    cfg["ab_custom_key"] = DEFAULTS["ab_custom_key"]
    for k, v in ab_key_vars.items():
        v.set(DEFAULTS["ab_keys"][k])
    ab_pmin_v.set(str(DEFAULTS["ab_pmin"]))
    ab_pmax_v.set(str(DEFAULTS["ab_pmax"]))
    ab_amax_v.set(str(DEFAULTS["ab_amax"]))
    ab_delay_v.set(str(DEFAULTS["ab_delay"]))
    ab_pixel_on_v.set(DEFAULTS["ab_pixel_on"])
    cfg["ab_pixel"] = None
    for k, (xv, yv) in cvars.items():
        xv.set(str(DEFAULTS[k][0]))
        yv.set(str(DEFAULTS[k][1]))
    save_settings()
    set_note("note_defaults")


save_b = tk.Button(btns, relief="flat", bd=0, font=(FONT, 10, "bold"), pady=12, cursor="hand2", command=save_settings)
TH(save_b, bg="ACC", fg=ACT_FG, activebackground="ACC_H", activeforeground=ACT_FG)
HoverFx(save_b, "ACC", "ACC_H")
L(save_b, "save")
save_b.pack(side="left", fill="x", expand=True, padx=(0, 8))
reset_b = tk.Button(btns, relief="flat", bd=0, font=(FONT, 10, "bold"), pady=12, cursor="hand2", command=reset_defaults)
TH(reset_b, bg="CARD", fg="TXT", activebackground="HOVER", activeforeground="TXT")
HoverFx(reset_b, "CARD", "HOVER")
L(reset_b, "reset")
reset_b.pack(side="left", fill="x", expand=True)
mk(st, bg="BG", font=(FONT, 8), textvariable=note_var).pack(pady=8)
mk(ab_page, bg="BG", font=(FONT, 8), textvariable=note_var).pack(pady=8)

# ---- Контроль команды ----
team_page = TH(tk.Frame(content), bg="BG")
pages["team"] = team_page
header(team_page, "td_title", "td_sub")
td_card = card(team_page)
td_card.pack(fill="x")
td_enabled_v = tk.BooleanVar(value=bool(cfg.get("td_enabled", False)))
Check(td_card, td_enabled_v, "td_enable",
      command=lambda: persist_preference("td_enabled", bool(td_enabled_v.get()))).grid(
    row=0, column=0, columnspan=4, sticky="w", pady=(0, 4))
td_status = tk.StringVar()
mk(td_card, textvariable=td_status, fg="MUT", font=(FONT, 8)).grid(row=1, column=0, columnspan=4, sticky="w", pady=(0, 8))
mk(td_card, "td_signs", fg="TXT", font=(FONT, 9, "bold")).grid(row=2, column=0, columnspan=4, sticky="w", pady=(0, 4))
td_ui = []
td_busy = [False]


def start_slot_capture(idx):
    """Через 4 секунды запоминает цвет под курсором: признак смерти игрока idx (0..3) или кнопку окна запуска (4)."""
    if td_busy[0]:
        return
    td_busy[0] = True
    name = t("td_player", idx + 1) if idx < 4 else t("td_popup")

    def tick(n):
        if n > 0:
            set_note("td_wait", name, n)
            root.after(1000, lambda: tick(n - 1))
            return
        td_busy[0] = False
        try:
            pos = pyautogui.position()
            shot = ImageGrab.grab(bbox=(pos.x - 2, pos.y - 2, pos.x + 3, pos.y + 3)).convert("RGB")
            col = "#%02x%02x%02x" % shot.resize((1, 1), _BOX).getpixel((0, 0))
            zone = [pos.x, pos.y, col]
            if idx < 4:
                cfg["td_slots"][idx] = zone
                persist_preference("td_slots", cfg["td_slots"])
            else:
                cfg["td_popup"] = zone
                persist_preference("td_popup", zone)
            set_note("td_slot_set", name, pos.x, pos.y, col)
        except Exception as e:
            log_error(traceback.format_exc())
            set_note("note_marker_err", str(e))
    tick(4)


for i in range(5):
    r = 3 + i
    lb = L(mk(td_card, fg="TXT", font=(FONT, 9)), "td_player", i + 1) if i < 4 else L(mk(td_card, fg="TXT", font=(FONT, 9)), "td_popup")
    lb.grid(row=r, column=0, sticky="w", pady=4)
    sw = tk.Label(td_card, width=3, bd=0)
    sw.grid(row=r, column=1, padx=10)
    info = tk.StringVar()
    mk(td_card, textvariable=info, fg="MUT", font=(FONT, 8)).grid(row=r, column=2, sticky="w", padx=(0, 12))
    b = tk.Button(td_card, relief="flat", bd=0, font=(FONT, 8, "bold"), padx=12, pady=4, cursor="hand2",
                  command=lambda i=i: start_slot_capture(i))
    TH(b, bg="BTN", fg="TXT", activebackground="ACC", activeforeground=ACT_FG)
    HoverFx(b, "BTN", "HOVER")
    L(b, "td_set")
    b.grid(row=r, column=3, sticky="e")
    td_ui.append((sw, info))
td_card.columnconfigure(2, weight=1)


def td_clear():
    cfg["td_slots"] = [None, None, None, None]
    cfg["td_popup"] = None
    persist_preference("td_slots", cfg["td_slots"])
    persist_preference("td_popup", None)


td_clear_b = tk.Button(td_card, relief="flat", bd=0, font=(FONT, 8, "bold"), padx=12, pady=4, cursor="hand2",
                       command=td_clear)
TH(td_clear_b, bg="BTN", fg="TXT", activebackground="ACC", activeforeground=ACT_FG)
HoverFx(td_clear_b, "BTN", "HOVER")
L(td_clear_b, "td_clear")
td_clear_b.grid(row=8, column=0, sticky="w", pady=(8, 0))
mk(td_card, "td_hint", font=(FONT, 8), wraplength=600, justify="left").grid(
    row=9, column=0, columnspan=4, sticky="w", pady=(8, 0))
mk(team_page, bg="BG", font=(FONT, 8), textvariable=note_var).pack(pady=8)


# ---- обновление и горячие клавиши ----
def refresh():
    status_var.set(t(state["phase"]))
    sub = state["sub"]
    sub_var.set(t(sub, state["sub_arg"]) if state.get("sub_arg") is not None else t(sub))
    rounds_var.set(str(state["rounds"]))
    dot.config(fg=P["GREEN"] if state["running"] else P["RED"])
    next_var.set(fmt(state["remaining"]) if state["running"] else fmt(cfg["match_min"] * 60))
    hint_var.set(t("hint", cfg["hotkey"].upper()))
    key_btn.config(text=t("press_key") if capture_target is key_btn else f"{cfg['hotkey'].upper()}  ·  {t('change')}")
    custom_btn.config(text=t("press_key") if capture_target is custom_btn
                      else f"{str(cfg.get('ab_custom_key', 'e')).upper()}  ·  {t('change')}")
    if state["running"]:
        start_btn.config(text=t("stop_queue"), activebackground=P["RED_H"])
    else:
        start_btn.config(text=t("start_queue"), activebackground=P["ACC_H"])
    start_fx.apply()
    px = cfg.get("ab_pixel")
    marker_sw.config(bg=px[2] if px else P["FIELD"])
    marker_info.set(f"{px[0]}, {px[1]}   {px[2]}" if px else t("marker_none"))
    for i, (sw, info) in enumerate(td_ui):
        z = cfg["td_slots"][i] if i < 4 else cfg.get("td_popup")
        sw.config(bg=z[2] if z else P["FIELD"])
        info.set(f"{z[0]}, {z[1]}  {z[2]}" if z else t("marker_none"))
    n_set = sum(1 for z in cfg["td_slots"] if z)
    td_status.set(t("td_state_off") if not cfg.get("td_enabled")
                  else t("td_state_ready") if n_set == 4 else t("td_state_incomplete", n_set))
    note_var.set(t(note_state[0], *note_state[1]))
    root.after(150, refresh)


def capture_marker():
    """F11: запоминает цвет пикселя под курсором как «маркер матча» (то, что видно только во время матча)."""
    try:
        pos = pyautogui.position()
        c = ImageGrab.grab(bbox=(pos.x, pos.y, pos.x + 1, pos.y + 1)).convert("RGB").getpixel((0, 0))
        col = "#%02x%02x%02x" % c
        cfg["ab_pixel"] = [pos.x, pos.y, col]
        ab_pixel_on_v.set(True)
        cfg["ab_pixel_on"] = True
        persist_preference("ab_pixel", cfg["ab_pixel"])
        set_note("note_marker", pos.x, pos.y, col)
    except Exception as e:
        log_error(traceback.format_exc())
        set_note("note_marker_err", str(e))


def copy_pos():
    p = pyautogui.position()
    root.clipboard_clear()
    root.clipboard_append(f"{p.x}, {p.y}")
    set_note("note_copied", p.x, p.y)


try:
    keyboard.add_hotkey("f9", lambda: root.after(0, copy_pos))
    keyboard.add_hotkey("f11", lambda: root.after(0, capture_marker))
    keyboard.add_hotkey("f10", lambda: root.after(0, quit_app))
except Exception:
    log_error(traceback.format_exc())


def on_tk_error(exc, val, tb):
    log_error("".join(traceback.format_exception(exc, val, tb)))
    set_note("sub_error", str(val))


root.report_callback_exception = on_tk_error
set_note("note_default")
bind_hotkey()
threading.Thread(target=hotkey_poll_loop, daemon=True).start()
threading.Thread(target=survey_watcher, daemon=True).start()
refresh_labels()
show("overview")
apply_theme(cfg["theme"])
apply_language()
refresh()
root.mainloop()
