from fastapi import FastAPI, Query, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uvicorn
import logging
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import your scraping function
from emergency_scraper import scrape_trains_between

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Train Info API...")
    yield
    logger.info("Shutting down Train Info API...")

app = FastAPI(
    title="Train Info API",
    description="API for fetching train information between stations",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8080",
        "https://yourdomain.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

class TrainInfo(BaseModel):
    train_number: str
    train_name: str
    train_type: str
    departure_time: str
    arrival_time: str
    duration: str
    source: str
    destination: str
    booking_classes: List[str] = []

class TrainResponse(BaseModel):
    success: bool
    data: List[TrainInfo]
    total_count: int
    timestamp: str
    message: Optional[str] = None

class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    timestamp: str

@app.get("/", response_model=dict)
async def root():
    return {
        "message": "Train Info API is running",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/trains/json", 
         response_model=TrainResponse,
         responses={
             200: {"description": "Successfully retrieved train data"},
             400: {"model": ErrorResponse},
             500: {"model": ErrorResponse}
         })
async def get_trains_json(
    src_name: str = Query(..., example="Howrah Jn"),
    src_code: str = Query(..., example="HWH"),
    dst_name: str = Query(..., example="Chittaranjan"),
    dst_code: str = Query(..., example="CRJ")
):
    try:
        if not all([src_name.strip(), src_code.strip(), dst_name.strip(), dst_code.strip()]):
            raise HTTPException(status_code=400, detail="All parameters must be provided")

        logger.info(f"Fetching trains from {src_name} ({src_code}) to {dst_name} ({dst_code})")

        trains = scrape_trains_between(src_name, src_code, dst_name, dst_code)
        if trains is None:
            return TrainResponse(
                success=True,
                data=[],
                total_count=0,
                timestamp=datetime.now().isoformat(),
                message="No trains found or invalid station code."
            )

        train_list = [
            TrainInfo(**t) for t in trains
        ]

        return TrainResponse(
            success=True,
            data=train_list,
            total_count=len(train_list),
            timestamp=datetime.now().isoformat(),
            message=f"Found {len(train_list)} trains"
        )

    except ValueError as ve:
        logger.warning(f"Validation error: {ve}")
        raise HTTPException(
            status_code=400,
            detail=str(ve)
        )
    except Exception as e:
        logger.error(f"Error fetching trains: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {e}"
        )

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "timestamp": datetime.now().isoformat()
        }
    )

if __name__ == "__main__":
    uvicorn.run("emergency_api:app", host="0.0.0.0", port=8000, reload=True)
