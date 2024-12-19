# src/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
import yaml
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
from api.models import (
    AutomationRequest,
    AutomationResponse,
    AutomationStatus,
    AutomationSession
)
from bot.core import JobApplicationBot, DEFAULT_CONFIG

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Storage for active bots
active_bots: Dict[str, JobApplicationBot] = {}

def load_config() -> dict:
    """Load configuration from YAML file"""
    try:
        config_path = Path("config/config.yaml")
        with open(config_path) as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        raise

app = FastAPI(
    title="Job Application Bot API",
    description="Automated job application service",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    logger.info("Root endpoint called")
    return {"message": "Job Application Bot API is running"}

@app.get("/health")
async def health_check():
    logger.info("Health check called")
    return {
        "status": "healthy",
        "active_bots": 0,#len(active_bots),
        "version": "1.0.0"
    }

@app.post("/api/v1/automation/start", response_model=AutomationResponse)
async def start_automation(request: AutomationRequest):
    logger.info(f"Starting automation for user: {request.user_id}")
    
    session_id = f"session_{request.user_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        # Create bot with form detection capability
        bot = JobApplicationBot(DEFAULT_CONFIG)
        
        # Test form detection
        detector = bot.form_detector
        logger.info("Form detector initialized successfully")
        
        return AutomationResponse(
            session_id=session_id,
            status=AutomationStatus.PENDING,
            message="Bot created successfully with form detection",
            estimated_completion=None
        )
        
    except Exception as e:
        logger.error(f"Failed to start automation: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@app.post("/api/v1/automation/{user_id}/stop")
async def stop_automation(user_id: str):
    """Stop automation process for a user"""
    try:
        bot = active_bots.get(user_id)
        if bot:
            await bot.cleanup()
            del active_bots[user_id]
            return {"message": "Automation stopped successfully"}
        return {"message": "No active automation found"}
        
    except Exception as e:
        logger.error(f"Failed to stop automation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/automation/{session_id}/status", response_model=AutomationSession)
async def get_automation_status(session_id: str):
    logger.info(f"Status check for session: {session_id}")
    
    bot = None #active_bots.get(session_id)
    if not bot:
        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )
    
    # Get bot stats
    stats = bot.get_stats()
    
    return AutomationSession(
        session_id=session_id,
        user_id="test_user",  # We'll add proper user tracking later
        status=AutomationStatus.RUNNING,
        start_time=datetime.utcnow(),
        applications_submitted=stats.get('successful', 0),
        applications_failed=stats.get('failed', 0)
    )


async def initialize_bot(user_id: str, config: dict) -> JobApplicationBot:
    """Initialize a new bot instance for a user"""
    try:
        bot = JobApplicationBot(config)
        if await bot.initialize():
            active_bots[user_id] = bot
            return bot
        raise Exception("Bot initialization failed")
    except Exception as e:
        logger.error(f"Failed to initialize bot for user {user_id}: {e}")
        raise

async def run_automation(user_id: str, request: AutomationRequest) -> None:
    """Background task for running the automation"""
    try:
        bot = active_bots.get(user_id)
        if not bot:
            bot = await initialize_bot(user_id, load_config())
        
        # Start automation process
        results = await bot.start_automation(request.job_preferences)
        
        # Update user's automation status
        await update_automation_status(
            user_id,
            AutomationStatus.COMPLETED,
            results=results
        )
        
    except Exception as e:
        logger.error(f"Automation failed for user {user_id}: {e}")
        await update_automation_status(
            user_id,
            AutomationStatus.FAILED,
            error=str(e)
        )

async def update_automation_status(
    user_id: str,
    status: AutomationStatus,
    results: Optional[list] = None,
    error: Optional[str] = None
) -> None:
    """Update automation status in database"""
    # TODO: Implement database update
    pass

if __name__ == "__main__":
    print("Starting application...")
    try:
        print("Starting server on http://127.0.0.1:8001")
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=8001,
            reload=False,
            log_level="debug"
        )
    except Exception as e:
        print(f"Error starting server: {str(e)}")
        raise