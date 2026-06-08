import json
import os
from PySide6.QtCore import QObject, Qt
from .path_utils import get_external_path

class ConfigManager(QObject):
    CONFIG_FILE = get_external_path(".smart_voca_config.json")
    
    SPECIAL_KEYS = {
        Qt.Key_Up: "Up",
        Qt.Key_Down: "Down",
        Qt.Key_Left: "Left",
        Qt.Key_Right: "Right",
        Qt.Key_Space: "Space",
        Qt.Key_Return: "Enter",
        Qt.Key_Enter: "Enter",
        Qt.Key_Backspace: "Backspace",
        Qt.Key_Delete: "Delete",
        Qt.Key_Tab: "Tab"
    }
    
    # In-memory storage
    _api_key = None
    _model_name = None
    _config_cache = None

    @staticmethod
    def _load_config():
        if os.path.exists(ConfigManager.CONFIG_FILE):
            try:
                with open(ConfigManager.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    @staticmethod
    def _ensure_loaded():
        """Ensures the config cache is populated."""
        if ConfigManager._config_cache is None:
            ConfigManager._config_cache = ConfigManager._load_config()

    @staticmethod
    def sync():
        """Saves the current in-memory config to the JSON file."""
        if ConfigManager._config_cache is None:
            return True
        try:
            with open(ConfigManager.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(ConfigManager._config_cache, f, ensure_ascii=False, indent=4)
            return True
        except:
            return False

    @staticmethod
    def set_api_key(api_key):
        """Saves the API key to memory (volatile)."""
        ConfigManager._api_key = api_key

    @staticmethod
    def get_api_key():
        """Retrieves the API key from memory."""
        return ConfigManager._api_key

    @staticmethod
    def save_model_name(model_name, persist=False, sync=True):
        """Updates the selected Gemini model name in the cache."""
        ConfigManager._model_name = model_name
        ConfigManager._ensure_loaded()
        if persist:
            ConfigManager._config_cache['model_name'] = model_name
        else:
            if 'model_name' in ConfigManager._config_cache:
                del ConfigManager._config_cache['model_name']
        
        if sync:
            ConfigManager.sync()        

    @staticmethod
    def get_model_name():
        """Retrieves the saved model name from cache."""
        if ConfigManager._model_name is None:
            ConfigManager._ensure_loaded()
            ConfigManager._model_name = ConfigManager._config_cache.get('model_name')
        return ConfigManager._model_name

    @staticmethod
    def save_env_var_name(name, sync=True):
        ConfigManager._ensure_loaded()
        ConfigManager._config_cache['env_var_name'] = name
        if sync:
            ConfigManager.sync()

    @staticmethod
    def get_env_var_name():
        ConfigManager._ensure_loaded()
        return ConfigManager._config_cache.get('env_var_name', 'GOOGLE_API_KEY')

    @staticmethod
    def save_app_mode(mode, sync=True):
        ConfigManager._ensure_loaded()
        ConfigManager._config_cache['app_mode'] = mode
        if sync:
            ConfigManager.sync()

    @staticmethod
    def get_app_mode():
        ConfigManager._ensure_loaded()
        return ConfigManager._config_cache.get('app_mode', 'personal')
    
    @staticmethod
    def save_prompt_filepath(filepath: str, sync=True):
        ConfigManager._ensure_loaded()
        ConfigManager._config_cache['prompt_filepath'] = filepath
        if sync:
            ConfigManager.sync()
    
    @staticmethod
    def get_prompt_filepath() -> str:
        ConfigManager._ensure_loaded()
        return ConfigManager._config_cache.get('prompt_filepath', '')

    @staticmethod
    def save_supabase_config(url, key, sync=True):
        ConfigManager._ensure_loaded()
        ConfigManager._config_cache['supabase_url'] = url
        ConfigManager._config_cache['supabase_key'] = key
        if sync:
            ConfigManager.sync()
        return True

    @staticmethod
    def get_supabase_config():
        ConfigManager._ensure_loaded()
        return ConfigManager._config_cache.get('supabase_url'), ConfigManager._config_cache.get('supabase_key')

    @staticmethod
    def save_sort_preference(view_key, index, sync=True):
        ConfigManager._ensure_loaded()
        ConfigManager._config_cache[f'{view_key}_sort_index'] = index
        if sync:
            ConfigManager.sync()
        return True

    @staticmethod
    def get_sort_preference(view_key, default=0):
        ConfigManager._ensure_loaded()
        return ConfigManager._config_cache.get(f'{view_key}_sort_index', default)

    @staticmethod
    def key_to_string(key_code):
        if key_code in ConfigManager.SPECIAL_KEYS:
            return ConfigManager.SPECIAL_KEYS[key_code]
        try:
            return chr(key_code).upper()
        except:
            return f"Key_{key_code}"

    @staticmethod
    def save_shortcuts(shortcuts, sync=True):
        ConfigManager._ensure_loaded()
        ConfigManager._config_cache['shortcuts'] = shortcuts
        if sync:
            ConfigManager.sync()
        return True

    @staticmethod
    def get_shortcuts():
        ConfigManager._ensure_loaded()
        defaults = {
            'tts': Qt.Key_Up,
            'star': Qt.Key_Down,
            'prev': Qt.Key_Left,
            'next': Qt.Key_Right,
            'flip': Qt.Key_Space
        }
        return ConfigManager._config_cache.get('shortcuts', defaults)

    @staticmethod
    def delete_api_key():
        ConfigManager._api_key = None
        ConfigManager._model_name = None
        return True