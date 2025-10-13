# TODO: Implement Accumulative Scoring and Feedback

## Backend Updates
- [x] Modify `core/session_store.py` to store FRS results in the DB (add table for session summaries with FRS data).
- [x] Update `api/routes/frs.py` to accumulate FRS scores during the WebSocket session (store scores in memory or DB per session).
- [x] Add an endpoint in `api/routes/session.py` to end the session and compute/store the final accumulated FRS (average or aggregate scores).
- [x] Update `main.py` to retrieve feedback from stored DB data instead of random generation (use stored FRS for feedback endpoint).
