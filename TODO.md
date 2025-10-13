# TODO: Fix Real-Time Analysis and Debugging

## Back-End Fixes (api/routes/frs.py)
- [x] Use asyncio.create_task for simulation loop to allow cancellation
- [x] Cancel simulation task on WebSocket disconnect
- [x] Add try-except around websocket.send_json with detailed logging
- [x] Print simulation data and FRS results to console for debugging

## Front-End Updates (static/index.html)
- [x] Add console.log for received WebSocket data
- [x] Add console.log for WebSocket errors and connection status
- [x] Display connection status in UI for better visibility

## Testing
- [ ] Run the app and test WebSocket connection
- [ ] Verify real-time updates in UI
- [ ] Check console logs for back-end and front-end activity
