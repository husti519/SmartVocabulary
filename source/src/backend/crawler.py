import os
import json
from google import genai
from google.genai import types

from ..utils.config_manager import ConfigManager
from ..utils.logger import log_exception
from PySide6.QtCore import QThread, Signal

class GeminiWorker(QThread):
    """Unified background worker for all Gemini AI tasks."""
    finished = Signal(str) # Returns the formatted definition string
    error = Signal(str)

    def __init__(self, word, prompt_template=None, api_key=None, model_name=None):
        super().__init__()
        self.word = word
        self.prompt_template = prompt_template
        self.api_key = api_key
        self.model_name = model_name

    def run(self):
        try:
            # Create a fresh provider instance for this thread
            provider = WordDataProvider()
            
            # Override settings if explicitly provided (for real-time tests)
            if self.api_key:
                provider.client = genai.Client(api_key=self.api_key)
            if self.model_name:
                provider.model_name = self.model_name
            if self.prompt_template:
                provider.prompt_template = self.prompt_template

            # Use the core logic to get data
            res = provider.get_full_data_from_gemini(self.word)
            if res:
                self.finished.emit(res)
            else:
                self.error.emit("No results found or AI response was empty.")
        except Exception as e:
            log_exception("GeminiWorker.run", "Background AI task failed", e)
            self.error.emit(str(e))

class WordDataProvider:
    def __init__(self):
        # Try to get API key from secure storage first, then environment
        self.api_key = ConfigManager.get_api_key()
        self.model_name = ConfigManager.get_model_name() or ""
        self.prompt_template = self.load_prompt()
        
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None
            print("Warning: Gemini API Key not found in secure storage or environment.")

    def load_prompt(self):
        """Loads the prompt template from an external file."""
        prompt_path = ConfigManager.get_resolved_prompt_filepath()
        default_prompt = """
        Provide detailed dictionary information for the English word '{word}'.
        Return ONLY a JSON object with the key "formatted_definition".
        """
        try:
            if os.path.exists(prompt_path):
                with open(prompt_path, "r", encoding="utf-8") as f:
                    return f.read()
        except Exception as e:
            log_exception("WordDataProvider.load_prompt", "Failed to load external prompt", e)
        return default_prompt

    def get_full_data_from_gemini(self, word):
        """Fetches structured dictionary data from Gemini using an external prompt template."""
        if not self.client:
            return ""

        # Format the template with the specific word
        prompt = self.prompt_template.replace("{word}", word)

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            data = json.loads(response.text)
            return data.get("formatted_definition", "")
        except Exception as e:
            log_exception("WordDataProvider.get_full_data_from_gemini", f"Error fetching data from Gemini for {word}", e)
            return ""

    def get_combined_data(self, word):
        """Gets the fully formatted definition from Gemini."""
        # Since the user wants a very specific layout where examples are interleaved with meanings,
        # it's best to let Gemini handle the entire structure.
        definition = self.get_full_data_from_gemini(word)
        
        if not definition:
            return None
            
        return {
            "word": word,
            "definition": definition
        }

    def format_definition(self, data):
        """The data already contains the fully formatted string from Gemini."""
        if not data:
            return ""
        return data.get("definition", "")
