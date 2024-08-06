import logging

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from hub.api.v1.exceptions import TokenValidationError
from hub.api.v1.routes import v1_router

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()
app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router, prefix="/v1")

# Deprecated, will be removed shortly
app.include_router(v1_router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.exception_handler(TokenValidationError)
async def token_validation_exception_handler(request, exc: TokenValidationError):
    lines = exc.detail.split('\n')
    error_message_short = '\n'.join(lines[:3])
    logger.info(f"Received invalid Auth Token: {error_message_short}")

    # 400 Bad Request if auth request was invalid
    return JSONResponse(status_code=400, content={"detail": f"Invalid auth data: {error_message_short}"})
