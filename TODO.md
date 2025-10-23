# TODO: Fix FRS Evaluation and Session Ending Issues

## Issues Identified
1. FRS evaluation printed inconsistently in backend (both WebSockets).
2. Real-time FRS not displayed in frontend due to data structure mismatch (backend sends 'frs_update' in voice_stream.py, frontend expects 'frs').
3. Accumulated result not displayed after ending session because /session/end computes its own averages instead of using accumulated_frs from frs.py.
4. End session button doesn't disconnect voiceWs socket, and voice_stream.py doesn't handle stop signals.
5. Hume client error: 'send_language' method not available.

## Plan
- [x] Fix Hume client send_language error by checking correct method.
- [ ] Unify FRS accumulation: modify /session/end to use accumulated_frs from frs.py.
- [ ] Fix data structure mismatch: ensure voice_stream.py sends 'frs' key instead of 'frs_update'.
- [ ] Add stop signal handling in voice_stream.py.
- [ ] Update frontend endSession to close both ws and voiceWs.
- [ ] Ensure FRS is printed consistently in both backends.

## Progress
- [x] Step 1: Fix Hume client send_language error
- [x] Step 2: Unify FRS accumulation in /session/end
- [x] Step 3: Fix data structure mismatch in voice_stream.py
- [x] Step 4: Add stop signal handling in voice_stream.py
- [ ] Step 5: Update frontend endSession to close both sockets
- [ ] Step 6: Ensure FRS printing consistency
