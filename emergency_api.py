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

# Replace with your actual import path
from emergency_scraper import scrape_trains_between

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Train Info API...")
    yield
    # Shutdown
    logger.info("Shutting down Train Info API...")

app = FastAPI(
    title="Train Info API",
    description="API for fetching train information between stations",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS - restrict origins in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://localhost:8080",  # Vue dev server
        "https://yourdomain.com"  # Production domain
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

class TrainInfo(BaseModel):
    train_number: str = Field(..., description="Train number")
    train_name: str = Field(..., description="Train name")
    train_type: str = Field(..., description="Type of train")
    departure_time: str = Field(..., description="Departure time")
    arrival_time: str = Field(..., description="Arrival time")
    duration: str = Field(..., description="Journey duration")
    source: str = Field(..., description="Source station")
    destination: str = Field(..., description="Destination station")
    booking_classes: List[str] = Field(default=[], description="Available booking classes")

class TrainResponse(BaseModel):
    success: bool = Field(..., description="Request success status")
    data: List[TrainInfo] = Field(..., description="List of trains")
    total_count: int = Field(..., description="Total number of trains")
    timestamp: str = Field(..., description="Response timestamp")
    message: Optional[str] = Field(None, description="Additional message")

class ErrorResponse(BaseModel):
    success: bool = Field(False, description="Request success status")
    error: str = Field(..., description="Error message")
    timestamp: str = Field(..., description="Error timestamp")

@app.get("/", response_model=dict)
async def root():
    """Health check endpoint"""
    return {
        "message": "Train Info API is running",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/trains/json", 
         response_model=TrainResponse,
         responses={
             200: {"description": "Successfully retrieved train data"},
             400: {"model": ErrorResponse, "description": "Bad request"},
             500: {"model": ErrorResponse, "description": "Internal server error"}
         })
async def get_trains_json(
    src_name: str = Query(..., example="Howrah Jn", description="Source station name"),
    src_code: str = Query(..., example="HWH", description="Source station code"),
    dst_name: str = Query(..., example="Chittaranjan", description="Destination station name"),
    dst_code: str = Query(..., example="CRJ", description="Destination station code")
):
    """
    Get train information between two stations.
    
    Returns a list of trains with their details including departure/arrival times,
    duration, and available booking classes.
    """
    try:
        # Input validation
        if not all([src_name.strip(), src_code.strip(), dst_name.strip(), dst_code.strip()]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="All parameters are required and cannot be empty"
            )
        
        # Log the request
        logger.info(f"Fetching trains from {src_name} ({src_code}) to {dst_name} ({dst_code})")
        
        # Call the scraper
        all_trains = scrape_trains_between(src_name, src_code, dst_name, dst_code)
        
        if not all_trains:
            return TrainResponse(
                success=True,
                data=[],
                total_count=0,
                timestamp=datetime.now().isoformat(),
                message="No trains found between the specified stations"
            )
        
        # Transform data
        result = [
            TrainInfo(
                train_number=t["train_number"],
                train_name=t["train_name"],
                train_type=t["train_type"],
                departure_time=t["departure_time"],
                arrival_time=t["arrival_time"],
                duration=t["duration"],
                source=t["source"],
                destination=t["destination"],
                booking_classes=t["booking_classes"] or []
            )
            for t in all_trains
        ]
        
        return TrainResponse(
            success=True,
            data=result,
            total_count=len(result),
            timestamp=datetime.now().isoformat(),
            message=f"Found {len(result)} trains"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log the error
        logger.error(f"Error fetching trains: {str(e)}", exc_info=True)
        
        # Return error response
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "Internal server error",
            "timestamp": datetime.now().isoformat()
        }
    )

if __name__ == "__main__":
    uvicorn.run(
        "emergency_api:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    ) 