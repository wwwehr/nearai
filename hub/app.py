import logging
from api.v1.routes import v1_router
from dotenv import load_dotenv
from fastapi import FastAPI

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()
app = FastAPI()
app.include_router(v1_router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok"}
