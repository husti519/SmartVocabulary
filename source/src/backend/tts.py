import os
from gtts import gTTS
import tempfile
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaDevices
from PySide6.QtCore import QUrl
import hashlib
from ..utils.logger import log_info

class TTSManager:
    def __init__(self):
        self.temp_dir = tempfile.gettempdir()
        # Initialize internal player
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(1.0)
        
        self.devices = QMediaDevices()
        # 시스템의 오디오 출력 장치가 변경되면 자동으로 함수 호출
        # ex) 내장 스피커에서 블루투스 스피커로 출력장지 변경할 때...
        self.devices.audioOutputsChanged.connect(self.update_audio_device)

    def speak(self, text, lang='en'):
        try:
            # Generate or reuse temp file
            safe_text = hashlib.md5(text.encode()).hexdigest()
            filename = os.path.join(self.temp_dir, f"tts_{safe_text}.mp3")
            
            if not os.path.exists(filename):
                tts = gTTS(text=text, lang=lang)
                tts.save(filename)
            
            self.play_audio(filename)
            return filename
        except Exception as e:
            # Minimal internal logging only if strictly necessary
            return None

    def play_audio(self, filename):
        """Plays the audio file internally using QtMultimedia."""
        self.player.setSource(QUrl.fromLocalFile(filename))
        self.player.play()
        
    def update_audio_device(self):
        # 현재 시점의 기본 장치를 가져옴
        current_device = QMediaDevices.defaultAudioOutput()
        log_info("TTS", f"Audio device change detected: {current_device.description()}")
        self.audio_output.setDevice(current_device)
