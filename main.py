from fastapi import FastAPI
from fastapi import FastAPI, status as HTTPStatus
from fastapi import HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import random
from datetime import datetime

from api.routes.frs import router as frs_router
from api.routes.session import router as session_router
from core.constant import Constant
from core.data_contract import DocumentationSections
from models.models import FRSResult, SessionSummary
from core.session_store import session_store

app = FastAPI(title=Constant.APPLICATION_NAME, version=Constant.APPLICATION_VERSION,
              swagger_ui_parameters={"defaultModelsExpandDepth": -1})

# In-memory storage for sessions (use a real DB in production)
sessions_db = {}

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers with prefixes
app.include_router(frs_router, prefix="/api", tags=["FRS"])
app.include_router(session_router, prefix="/session", tags=["Session"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this to specific domains for security
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

@app.get("/docs", include_in_schema=False, tags=[DocumentationSections.DOCUMENTATION])
async def custom_swagger_ui_html():
    """
    This endpoint returns the Swagger UI page for the API.
    """
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="FastAPI Swagger UI"
    )

@app.get("/openapi.json", include_in_schema=False, tags=[DocumentationSections.DOCUMENTATION])
async def get_open_api_endpoint() -> dict:
    """
    This endpoint returns the OpenAPI schema for the API. The OpenAPI schema is a JSON object that describes the API's endpoints, methods, parameters, and responses. It is used by tools like Swagger UI to generate an interactive API documentation.

    Returns:
        A JSON object containing the OpenAPI schema.
    """
    return app.openapi()

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
            "stars_earned": summary['stars_earned']
        }

    # If no summary, compute from accumulated FRS scores
    from api.routes.frs import accumulated_frs
    frs_scores = accumulated_frs.get(session_id, [])
    if not frs_scores:
        raise HTTPException(status_code=404, detail="No FRS data found for session")

    # Calculate averages
    num_scores = len(frs_scores)
    avg_charisma_friendliness = sum(score['charisma_friendliness'] for score in frs_scores) / num_scores
    avg_emotional_attunement_empathy = sum(score['emotional_attunement_empathy'] for score in frs_scores) / num_scores
    avg_confidence_selfregulation = sum(score['confidence_selfregulation'] for score in frs_scores) / num_scores
    avg_listening_reciprocal = sum(score['listening_reciprocal'] for score in frs_scores) / num_scores
    avg_frs_score = sum(score['frs_score'] for score in frs_scores) / num_scores

    # Determine medals and stars
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

    # Additional medals
    if avg_charisma_friendliness > 0.8:
        if "Persuasion" not in medals:
            medals.append("Persuasion")
    if avg_emotional_attunement_empathy > 0.8:
        if "Compassion" not in medals:
            medals.append("Compassion")
    if avg_confidence_selfregulation > 0.8:
        if "Clarity" not in medals:
            medals.append("Clarity")
    if avg_listening_reciprocal > 0.8:
        if "Adaptability" not in medals:
            medals.append("Adaptability")

    # Generate feedback
    if avg_frs_score >= 8.0:
        feedback = "Excellent performance! You're a natural at social interactions."
    elif avg_frs_score >= 6.0:
        feedback = "Good job! With a bit more practice, you'll excel."
    else:
        feedback = "Keep practicing! Focus on eye contact and engagement."

    return {
        "overall_frs": round(avg_frs_score, 1),  # Match the format expected by frontend
        "breakdown": {
            "charisma_friendliness": round(avg_charisma_friendliness, 2),
            "emotional_attunement_empathy": round(avg_emotional_attunement_empathy, 2),
            "confidence_selfregulation": round(avg_confidence_selfregulation, 2),
            "listening_reciprocal": round(avg_listening_reciprocal, 2)
        },
        "medals": medals,
        "objectives_completed": [],  # No objectives completed without session summary
        "feedback": feedback,
        "stars_earned": stars_earned
    }

@app.get("/")
async def serve_frontend():
    """
    Serve the main frontend page.
    """
    return FileResponse("static/index.html")

