"""
Voice/Speech Skill — الصوت والكلام
====================================
Text-to-speech and speech-to-text capabilities.
Supports voice-based property listings and voice interactions.
"""

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger("skills.voice_speech")


class VoiceSpeechSkill:
    """Text-to-speech and speech-to-text skill."""

    async def text_to_speech(self, text: str, output_path: str = "output.mp3") -> dict:
        """Convert text to speech using OpenAI TTS."""
        try:
            import openai

            api_key = os.getenv("OPENAI_API_KEY", "")
            if not api_key:
                # Fallback: use pyttsx3 for offline TTS
                return await self._tts_pyttsx3(text, output_path)

            client = openai.OpenAI(api_key=api_key)
            response = client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input=text[:4096],
            )

            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            response.stream_to_file(output_path)

            return {
                "status": "success",
                "file": output_path,
                "engine": "openai",
                "text_length": len(text),
            }
        except ImportError:
            return await self._tts_pyttsx3(text, output_path)
        except Exception:
            return await self._tts_pyttsx3(text, output_path)

    async def _tts_pyttsx3(self, text: str, output_path: str) -> dict:
        """Fallback TTS using pyttsx3."""
        try:
            import pyttsx3

            engine = pyttsx3.init()
            engine.setProperty("rate", 150)
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            engine.save_to_file(text[:5000], output_path)
            engine.runAndWait()

            return {
                "status": "success",
                "file": output_path,
                "engine": "pyttsx3",
                "text_length": len(text),
            }
        except ImportError:
            return {"status": "error", "error": "No TTS engine available. Install openai or pyttsx3."}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def speech_to_text(self, audio_path: str) -> dict:
        """Convert speech to text using OpenAI Whisper."""
        try:
            import openai

            api_key = os.getenv("OPENAI_API_KEY", "")
            if not api_key:
                return {"status": "error", "error": "OPENAI_API_KEY required for STT"}

            if not Path(audio_path).exists():
                return {"status": "error", "error": f"Audio file not found: {audio_path}"}

            client = openai.OpenAI(api_key=api_key)
            with open(audio_path, "rb") as audio_file:
                response = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                )

            return {
                "status": "success",
                "file": audio_path,
                "transcription": response.text,
                "engine": "whisper",
            }
        except ImportError:
            return {"status": "error", "error": "openai not installed. Run: pip install openai"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def generate_property_description(self, property_data: dict) -> str:
        """Generate a spoken description of a property."""
        description = f"""
Welcome to this property listing.

The property is located at {property_data.get('address', 'N/A')}.
It is priced at {property_data.get('price', 'N/A')} Egyptian Pounds.

The property features:
- Area: {property_data.get('area', 'N/A')} square meters
- {property_data.get('bedrooms', 'N/A')} bedrooms
- {property_data.get('bathrooms', 'N/A')} bathrooms
"""
        if property_data.get("features"):
            description += "\nAdditional features include:\n"
            for feature in property_data["features"][:5]:
                description += f"- {feature}\n"

        description += "\nContact us for viewing appointments."
        return description.strip()

    async def generate_viewing_script(self, property_data: dict) -> str:
        """Generate a script for virtual property viewing."""
        return f"""
Hello! Welcome to our virtual property viewing.

We are currently at {property_data.get('address', 'this property')}.

This {property_data.get('bedrooms', '')}-bedroom property spans {property_data.get('area', 'N/A')} square meters.

As you can see, the property offers {property_data.get('condition', 'good')} condition
and is located in {property_data.get('neighborhood', 'a desirable area')}.

The asking price is {property_data.get('price', 'N/A')} Egyptian Pounds.

Let me show you around the main areas...
""".strip()


def get_voice_tools():
    """Return CrewAI-compatible tools for voice/speech."""
    from crewai.tools import BaseTool
    from pydantic import BaseModel, Field

    class TextToSpeechInput(BaseModel):
        text: str = Field(description="Text to convert to speech")
        output_path: str = Field(default="output.mp3", description="Output audio file path")

    class TextToSpeechTool(BaseTool):
        name: str = "text_to_speech"
        description: str = "Convert text to speech audio file."
        args_schema: type = TextToSpeechInput

        def _run(self, text: str, output_path: str = "output.mp3") -> str:
            import asyncio
            skill = VoiceSpeechSkill()
            result = asyncio.run(skill.text_to_speech(text, output_path))
            return json.dumps(result, ensure_ascii=False)

    class SpeechToTextInput(BaseModel):
        audio_path: str = Field(description="Path to audio file")

    class SpeechToTextTool(BaseTool):
        name: str = "speech_to_text"
        description: str = "Transcribe an audio file to text."
        args_schema: type = SpeechToTextInput

        def _run(self, audio_path: str) -> str:
            import asyncio
            skill = VoiceSpeechSkill()
            result = asyncio.run(skill.speech_to_text(audio_path))
            return json.dumps(result, ensure_ascii=False)

    return [TextToSpeechTool(), SpeechToTextTool()]
