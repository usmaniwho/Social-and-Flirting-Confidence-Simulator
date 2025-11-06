import asyncio
import websockets
import json
import base64
import wave
import struct
import io
import math

async def send_beep():
    try:
        uri = 'ws://localhost:8000/api/realtime/voice-stream'
        print('Connecting to WebSocket...')
        async with websockets.connect(uri) as websocket:
            print('Connected successfully!')

            # Generate a beep WAV file in memory
            sample_rate = 44100
            duration = 1.0
            frequency = 440.0
            num_samples = int(duration * sample_rate)

            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                for i in range(num_samples):
                    t = i / sample_rate
                    fade = min(t * 10, (duration - t) * 10, 1.0)
                    sample = int(32767 * fade * math.sin(2 * math.pi * frequency * t))
                    wav_file.writeframes(struct.pack('<h', sample))

            wav_data = wav_buffer.getvalue()
            audio_b64 = base64.b64encode(wav_data).decode('utf-8')

            # Send the beep audio
            payload = {
                'session_id': 'test-beep-session',
                'audio': audio_b64
            }

            await websocket.send(json.dumps(payload))
            print('Sent beep audio to WebSocket')

            # Wait for response
            try:
                response = await websocket.recv()
                data = json.loads(response)
                print('Received response:', data)

                if 'user_text' in data:
                    print(f'User transcription: \"{data['user_text']}\"')
                if 'reply_text' in data:
                    print(f'AI response: \"{data['reply_text']}\"')

            except Exception as e:
                print(f'Error receiving response: {e}')

    except Exception as e:
        print(f'Error: {e}')

asyncio.run(send_beep())
