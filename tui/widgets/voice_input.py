"""Voice input widget for cat-pointer game"""

import asyncio
import io
import os
import tempfile
import threading
from typing import Any, ClassVar

from textual.binding import Binding
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Button, Static

# Optional imports for voice functionality
try:
    import sounddevice as sd
    from scipy.io import wavfile
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False


class VoiceInput(Horizontal):
    """Voice input widget with recording button"""

    DEFAULT_CSS = """
    VoiceInput {
        height: 3;
        width: 100%;
        padding: 0 1;
        background: $surface;
        align: center middle;
    }

    VoiceInput .voice-btn {
        width: auto;
        min-width: 16;
        height: 3;
        margin: 0 1;
    }

    VoiceInput .voice-btn.recording {
        background: $error;
    }

    VoiceInput .voice-status {
        width: 1fr;
        height: 1;
        padding: 0 1;
        color: $text-muted;
    }
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("ctrl+r", "toggle_recording", "录音", show=False),
    ]

    class Transcribed(Message):
        """Message sent when voice is transcribed"""

        def __init__(self, text: str) -> None:
            super().__init__()
            self.text = text

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._recording = False
        self._audio_data: list = []
        self._sample_rate = 16000
        self._record_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def compose(self):
        """Compose layout"""
        yield Button("🎤 按住说话", id="voice-btn", classes="voice-btn")
        yield Static("Ctrl+R 开始/停止录音", classes="voice-status", id="voice-status")

    def on_mount(self) -> None:
        """Initialize after mount"""
        if not VOICE_AVAILABLE:
            status = self.query_one("#voice-status", Static)
            status.update("⚠ 语音功能不可用 (需要 sounddevice, scipy)")
            btn = self.query_one("#voice-btn", Button)
            btn.disabled = True

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press"""
        if event.button.id == "voice-btn":
            self.action_toggle_recording()

    def action_toggle_recording(self) -> None:
        """Toggle recording state"""
        if not VOICE_AVAILABLE:
            self.notify("语音功能不可用，请安装 sounddevice 和 scipy", severity="warning")
            return

        if self._recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self) -> None:
        """Start recording audio"""
        self._recording = True
        self._audio_data = []
        self._stop_event.clear()

        btn = self.query_one("#voice-btn", Button)
        btn.label = "🔴 录音中..."
        btn.add_class("recording")

        status = self.query_one("#voice-status", Static)
        status.update("正在录音，再次点击或按 Ctrl+R 停止")

        # Start recording in background thread
        self._record_thread = threading.Thread(target=self._record_audio)
        self._record_thread.start()

    def _record_audio(self) -> None:
        """Record audio in background thread"""
        try:
            with sd.InputStream(
                samplerate=self._sample_rate,
                channels=1,
                dtype='int16',
                callback=self._audio_callback,
            ):
                while not self._stop_event.is_set():
                    sd.sleep(100)
        except Exception as e:
            self.app.call_from_thread(
                self.notify, f"录音错误: {str(e)}", severity="error"
            )

    def _audio_callback(self, indata, frames, time, status):
        """Callback for audio stream"""
        if status:
            print(f"Audio status: {status}")
        self._audio_data.append(indata.copy())

    def _stop_recording(self) -> None:
        """Stop recording and transcribe"""
        self._recording = False
        self._stop_event.set()

        btn = self.query_one("#voice-btn", Button)
        btn.label = "🎤 按住说话"
        btn.remove_class("recording")

        status = self.query_one("#voice-status", Static)
        status.update("正在转写...")

        if self._record_thread:
            self._record_thread.join(timeout=1.0)
            self._record_thread = None

        # Transcribe in background
        self.run_worker(self._transcribe_audio())

    async def _transcribe_audio(self) -> None:
        """Transcribe recorded audio using Whisper API"""
        import numpy as np

        if not self._audio_data:
            status = self.query_one("#voice-status", Static)
            status.update("没有录到音频")
            return

        # Combine audio chunks
        audio = np.concatenate(self._audio_data, axis=0)

        # Save to temporary WAV file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
            wavfile.write(temp_path, self._sample_rate, audio)

        try:
            # Call Whisper API
            text = await self._call_whisper_api(temp_path)

            if text:
                status = self.query_one("#voice-status", Static)
                status.update(f"识别结果: {text}")
                self.post_message(self.Transcribed(text))
            else:
                status = self.query_one("#voice-status", Static)
                status.update("未能识别语音")
        except Exception as e:
            status = self.query_one("#voice-status", Static)
            status.update(f"转写失败: {str(e)}")
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except Exception:
                pass

    async def _call_whisper_api(self, audio_path: str) -> str:
        """Call OpenAI Whisper API for transcription"""
        import httpx

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set")

        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

        async with httpx.AsyncClient() as client:
            with open(audio_path, "rb") as f:
                response = await client.post(
                    f"{base_url}/audio/transcriptions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    files={"file": ("audio.wav", f, "audio/wav")},
                    data={"model": "whisper-1", "language": "zh"},
                    timeout=30.0,
                )

            if response.status_code != 200:
                raise Exception(f"Whisper API error: {response.text}")

            result = response.json()
            return result.get("text", "").strip()
