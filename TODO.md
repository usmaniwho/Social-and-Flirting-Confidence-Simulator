# TODO: Integrate Hume AI Streaming API into Voice Stream Endpoint

## Steps to Complete

- [x] Step 1: Update hume_ai/__init__.py to properly export HumeStreamClient if needed.
- [x] Step 2: Modify api/routes/voice_stream.py to instantiate HumeStreamClient per WebSocket connection.
- [x] Step 3: On WebSocket accept, establish connection to Hume stream using connect().
- [x] Step 4: For each incoming message, send audio data via send_mic_data().
- [x] Step 5: Start receive_loop in a background asyncio task to collect emotions via callback.
- [x] Step 6: Collect and use the latest emotions for FRS computation and GPT response generation.
- [x] Step 7: Ensure proper disconnection on WebSocket close.
- [ ] Step 8: Test the integration by running the server and checking WebSocket behavior.
