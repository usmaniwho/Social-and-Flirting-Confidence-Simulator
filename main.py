from fastapi import FastAPI
from fastapi import FastAPI, status as HTTPStatus
from fastapi import HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse


from api.routes.frs import router as frs_router
from api.routes.session import router as session_router
from core.constant import Constant
from core.data_contract import DocumentationSections

app = FastAPI(title=Constant.APPLICATION_NAME, version=Constant.APPLICATION_VERSION,
              swagger_ui_parameters={"defaultModelsExpandDepth": -1})

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
    Get post-session feedback screen data.
    """
    # Placeholder: fetch from DB
    return {
        "overall_frs": 7.5,
        "breakdown": {
            "visual_confidence": 0.8,
            "vocal_fluency": 0.7,
            "emotional_awareness": 0.75
        },
        "medals": ["Charisma", "Friendliness"],
        "objectives_completed": ["Deepen conversation", "Eye contact"]
    }

@app.get("/")
async def serve_frontend():
    """
    Serve the main frontend page.
    """
    return FileResponse("static/index.html")

