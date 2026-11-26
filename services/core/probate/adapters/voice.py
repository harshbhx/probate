"""Voices for eulogies and ancestor answers (ElevenLabs through the gateway).

The fake returns None, and the UI then shows the transcript only.
"""

from __future__ import annotations

from probate.common.http import gateway_client

VOICE_POOL = [
    "voice-pool-01",
    "voice-pool-02",
    "voice-pool-03",
    "voice-pool-04",
    "voice-pool-05",
    "voice-pool-06",
    "voice-pool-07",
    "voice-pool-08",
    "voice-pool-09",
    "voice-pool-10",
    "voice-pool-11",
    "voice-pool-12",
]  # replaced by real ElevenLabs voice IDs after spike S8 (scripts/spike_voice_llm.py prints them)


class FakeVoice:
    def speak(self, text: str, voice_id: str | None) -> bytes | None:
        return None


class ElevenLabsVoice:
    def __init__(
        self, base_url: str, model: str = "eleven_multilingual_v2", timeout: float = 60
    ) -> None:
        self.base = base_url.rstrip("/")
        self.model = model
        self.http = gateway_client(timeout=timeout)

    def speak(self, text: str, voice_id: str | None) -> bytes | None:
        if not voice_id:
            return None
        # VERIFY in spike S8: path as shown on the connector's API Usage panel
        r = self.http.post(
            f"{self.base}/v1/text-to-speech/{voice_id}",
            json={"text": text, "model_id": self.model},
            headers={"Accept": "audio/mpeg"},
        )
        return r.content if r.status_code == 200 else None
