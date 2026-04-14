#!/usr/bin/env python3
"""Text-to-speech provider abstraction and OpenAI implementation."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol


class TTSError(Exception):
    """Raised when text-to-speech synthesis fails."""


class TTSProvider(Protocol):
    """Protocol for pluggable TTS providers."""

    def synthesize(self, text: str, *, voice: str) -> bytes:
        """Synthesize text and return audio payload bytes."""


@dataclass(frozen=True)
class OpenAITTSProvider:
    """OpenAI TTS implementation using server-side HTTP calls."""

    api_key: str
    model: str = 'gpt-4o-mini-tts'
    response_format: str = 'mp3'

    def synthesize(self, text: str, *, voice: str) -> bytes:
        payload = {
            'model': self.model,
            'voice': voice,
            'input': text,
            'response_format': self.response_format,
        }
        req = urllib.request.Request(
            'https://api.openai.com/v1/audio/speech',
            data=json.dumps(payload).encode('utf-8'),
            method='POST',
            headers={
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            if exc.code == 401:
                raise TTSError('TTS authentication failed')
            if exc.code == 429:
                raise TTSError('TTS rate limit exceeded')
            raise TTSError('TTS provider temporarily unavailable')
        except urllib.error.URLError:
            raise TTSError('TTS provider temporarily unavailable')
        except Exception:
            raise TTSError('TTS provider temporarily unavailable')
