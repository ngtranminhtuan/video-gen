from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import logging
from app.api import video, tts, video_story

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Video Generation API",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    swagger_ui_parameters={"syntaxHighlight.theme": "monokai", "tryItOutEnabled": True, "persistAuthorization": True, "displayRequestDuration": True, "filter": True, "docExpansion": "none", "defaultModelsExpandDepth": -1, "displayOperationId": False, "supportedSubmitMethods": ["get", "post", "put", "delete"]}
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket route
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, clientId: str = None):
    await websocket.accept()
    logger.info(f"WebSocket connection accepted for client: {clientId}")
    try:
        while True:
            data = await websocket.receive_text()
            logger.info(f"Received WebSocket data: {data[:100]}...")
            await websocket.send_text(f"Message received")
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for client: {clientId}")

# Include routers
app.include_router(video.router, prefix="/api/v1", tags=["video"])
app.include_router(tts.router, prefix="/api/v1", tags=["tts"])
app.include_router(video_story.router, prefix="/api/v1", tags=["video-story"])

logger.info("Application started")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 