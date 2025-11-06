# TODO: Implement GPT Functionality for Audio Upload

## Overview
Implement a POST endpoint `/audio_response/{session_id}` in `session.py` that handles the full audio-to-response pipeline: STT (Whisper) → GPT → TTS (ElevenLabs) → Return text + audio.

## Steps
- [ ] Add new endpoint `/audio_response/{session_id}` in `api/routes/session.py`
  - Accept POST with `session_id` and `audio` (base64 encoded)
  - Decode audio bytes
  - Transcribe audio to text using Whisper (via `gpt_client.transcribe_audio`)
  - Retrieve conversation history from session
  - Generate GPT response using `gpt_client.generate_response`
  - Generate TTS audio using `ElevenLabsClient.generate_speech`
  - Update conversation history in session store
  - Optionally, analyze emotions with Hume AI for FRS scoring
  - Return JSON: `{"response": text, "audio": base64_audio, "user_text": transcribed_text, "emotions": {...}}`
- [ ] Test the endpoint with sample audio
- [ ] Ensure error handling for transcription, GPT, TTS failures
- [ ] Update session store with new conversation entries
- [ ] Integrate FRS scoring if emotions are analyzed

## Dependencies
- Whisper API (OpenAI)
- GPT-4o-mini
- ElevenLabs TTS
- Hume AI for emotions (optional)

## Notes
- Audio format: Assume base64 encoded WAV/MP3/WebM, convert if needed (use pydub as in voice_stream.py)
- Personality: Use session's personality
- Conversation history: Keep last 20 messages
