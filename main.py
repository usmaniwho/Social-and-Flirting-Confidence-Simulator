# main.py

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime

# ✅ Routers
from api.routes.frs import router as frs_router
from api.routes.session import router as session_router
from api.routes.conversation import router as conversation_router

from core.constant import Constant
from core.data_contract import DocumentationSections
from core.session_store import session_store
from models.models import CalibrationStep


app = FastAPI(
    title=Constant.APPLICATION_NAME,
    version=Constant.APPLICATION_VERSION,
    swagger_ui_parameters={"defaultModelsExpandDepth": -1}
)

# In-memory fallback session cache (for temp data)
sessions_db = {}

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# ✅ NEW: Import real-time voice router
# -------------------------------------
# 💡 CHANGE: Added this import for the WebSocket voice call flow
from api.routes.voice_stream import router as voice_router

# ✅ Include all routers
app.include_router(frs_router, prefix="/api", tags=["FRS"])
app.include_router(session_router, prefix="/session", tags=["Session"])
app.include_router(conversation_router, prefix="/api", tags=["Conversation"])
app.include_router(voice_router, prefix="/realtime", tags=["Voice Stream"])

# Add calibration steps endpoint
@app.get("/api/calibration/steps")
def get_calibration_steps():
    """
    Get calibration steps for initial baseline establishment.
    """
    steps = [
        CalibrationStep(
            step_id="line_1",
            instruction="Read aloud in a neutral tone",
            line_to_read="Hey there! I saw you across the room and figured I'd come say hi."
        ),
        CalibrationStep(
            step_id="line_2",
            instruction="Read aloud in a friendly tone",
            line_to_read="Hi! I'm really enjoying this event so far."
        ),
        CalibrationStep(
            step_id="line_3",
            instruction="Read aloud in a flirtatious tone",
            line_to_read="You have such an interesting energy about you."
        ),
        CalibrationStep(
            step_id="line_4",
            instruction="Read aloud in an assertive tone",
            line_to_read="I'd love to continue this conversation if you're free."
        ),
        CalibrationStep(
            step_id="expression_1",
            instruction="Show a genuine smile",
            expression="smiling"
        ),
        CalibrationStep(
            step_id="expression_2",
            instruction="Show curiosity",
            expression="curiosity"
        ),
        CalibrationStep(
            step_id="expression_3",
            instruction="Show playful tone",
            expression="playful"
        ),
        CalibrationStep(
            step_id="expression_4",
            instruction="Show sincere interest",
            expression="sincere_interest"
        ),
        CalibrationStep(
            step_id="gesture_1",
            instruction="Lean in slightly",
            gesture="lean_in"
        ),
        CalibrationStep(
            step_id="gesture_2",
            instruction="Shrug casually",
            gesture="shrug"
        ),
        CalibrationStep(
            step_id="gesture_3",
            instruction="Nod in agreement",
            gesture="nod"
        )
    ]
    return {"steps": [step.dict() for step in steps]}

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or ["http://localhost:5500"] if using Live Server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_websocket_origins=["*"],
)

# -------------------------------
# 🧭 API Documentation & Docs UI
# -------------------------------

@app.get("/docs", include_in_schema=False, tags=[DocumentationSections.DOCUMENTATION])
async def custom_swagger_ui_html():
    """Custom Swagger UI"""
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="FastAPI Swagger UI"
    )

@app.get("/openapi.json", include_in_schema=False, tags=[DocumentationSections.DOCUMENTATION])
async def get_open_api_endpoint() -> dict:
    """Return OpenAPI schema"""
    return app.openapi()


# -------------------------------
# 🌟 FEEDBACK ENDPOINT
# -------------------------------

@app.get("/feedback/{session_id}")
def get_feedback_screen(session_id: str):
    """
    Get post-session feedback screen data from stored DB summary or compute from accumulated FRS.
    """
    summary = session_store.get_session_summary(session_id)
    if summary:
        frs_result = summary['frs_result']
        return {
            "overall_frs": frs_result['frs_score'],
            "breakdown": {
                "charisma_friendliness": frs_result['charisma_friendliness'],
                "emotional_attunement_empathy": frs_result['emotional_attunement_empathy'],
                "confidence_selfregulation": frs_result['confidence_selfregulation'],
                "listening_reciprocal": frs_result['listening_reciprocal']
            },
            "medals": frs_result['medals'],
            "objectives_completed": summary['objectives_completed'],
            "feedback": summary['feedback'],
            "stars_earned": summary['stars_earned'],
            "personality": summary.get('personality')
        }

    # If no summary found → compute average from live session scores
    from api.routes.frs import accumulated_frs
    frs_scores = accumulated_frs.get(session_id, [])
    if not frs_scores:
        raise HTTPException(status_code=404, detail="No FRS data found for session")

    # Average out scores
    num_scores = len(frs_scores)
    avg_frs_score = sum(score['frs_score'] for score in frs_scores) / num_scores

    avg_charisma_friendliness = sum(score['charisma_friendliness'] for score in frs_scores) / num_scores
    avg_emotional_attunement_empathy = sum(score['emotional_attunement_empathy'] for score in frs_scores) / num_scores
    avg_confidence_selfregulation = sum(score['confidence_selfregulation'] for score in frs_scores) / num_scores
    avg_listening_reciprocal = sum(score['listening_reciprocal'] for score in frs_scores) / num_scores

    medals = []
    stars_earned = 1
    if avg_frs_score >= 8.5:
        medals.extend(["Charisma", "Friendliness", "Composure", "Awareness"])
        stars_earned = 4
    elif avg_frs_score >= 7.0:
        medals.extend(["Charisma", "Friendliness", "Composure"])
        stars_earned = 3
    elif avg_frs_score >= 5.5:
        medals.extend(["Friendliness", "Composure"])
        stars_earned = 2
    elif avg_frs_score >= 4.0:
        medals.append("Composure")
        stars_earned = 1

    if avg_charisma_friendliness > 0.8 and "Persuasion" not in medals:
        medals.append("Persuasion")
    if avg_emotional_attunement_empathy > 0.8 and "Compassion" not in medals:
        medals.append("Compassion")
    if avg_confidence_selfregulation > 0.8 and "Clarity" not in medals:
        medals.append("Clarity")
    if avg_listening_reciprocal > 0.8 and "Adaptability" not in medals:
        medals.append("Adaptability")

    if avg_frs_score >= 8.0:
        feedback = "Excellent performance! You're a natural at social interactions."
    elif avg_frs_score >= 6.0:
        feedback = "Good job! With a bit more practice, you'll excel."
    else:
        feedback = "Keep practicing! Focus on eye contact and engagement."

    return {
        "final_frs": {
            "frs_score": round(avg_frs_score, 1),
            "charisma_friendliness": round(avg_charisma_friendliness, 2),
            "emotional_attunement_empathy": round(avg_emotional_attunement_empathy, 2),
            "confidence_selfregulation": round(avg_confidence_selfregulation, 2),
            "listening_reciprocal": round(avg_listening_reciprocal, 2),
            "medals": medals
        },
        "feedback": {
            "overall": feedback
        },
        "objectives_completed": [],
        "transcript": [],
        "stars_earned": stars_earned
    }


# -------------------------------
# 🖥️ FRONTEND SERVE
# -------------------------------
@app.get("/")
async def serve_frontend():
    """Serve main frontend HTML"""
    return FileResponse("static/index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)