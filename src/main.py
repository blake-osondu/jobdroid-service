import asyncio
import yaml
import argparse
import logging
from pathlib import Path
from typing import Dict, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from bot.core import JobApplicationBot
from api.models import (
    UserProfile, 
    AutomationRequest, 
    AutomationResponse, 
    AutomationStatus
)
from utils.logger import JobBotLogger

# Initialize FastAPI app
app = FastAPI(
    title="Job Application Bot API",
    description="Automated job application service",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
active_bots: Dict[str, JobApplicationBot] = {}
logger = JobBotLogger(__name__)

def load_config() -> dict:
    """Load configuration from YAML file"""
    try:
        config_path = Path("config/config.yaml")
        with open(config_path) as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        raise

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

@app.post("/api/v1/automation/start")
async def start_automation(
    request: AutomationRequest,
    background_tasks: BackgroundTasks
):
    """Start automation process for a user"""
    try:
        # Validate user and request
        if not request.user_id:
            raise HTTPException(status_code=400, message="User ID is required")
            
        # Add automation task to background tasks
        background_tasks.add_task(run_automation, request.user_id, request)
        
        return AutomationResponse(
            session_id=f"session_{request.user_id}",
            status=AutomationStatus.PENDING,
            message="Automation started successfully"
        )
        
    except Exception as e:
        logger.error(f"Failed to start automation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/automation/{user_id}/status")
async def get_automation_status(user_id: str):
    """Get current automation status for a user"""
    try:
        bot = active_bots.get(user_id)
        if not bot:
            return {
                "status": "NOT_FOUND",
                "message": "No active automation session found"
            }
            
        stats = bot.get_stats()
        return {
            "status": "ACTIVE" if stats['total_attempts'] > 0 else "IDLE",
            "statistics": stats
        }
        
    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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

@app.get("/api/v1/health")
async def health_check():
    """API health check endpoint"""
    return {
        "status": "healthy",
        "active_sessions": len(active_bots),
        "version": "1.0.0"
    }

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Job Application Bot")
    parser.add_argument(
        "--config",
        type=str,
        default="config/config.yaml",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )
    return parser.parse_args()

async def cleanup():
    """Cleanup resources on shutdown"""
    for user_id, bot in active_bots.items():
        try:
            await bot.cleanup()
        except Exception as e:
            logger.error(f"Failed to cleanup bot for user {user_id}: {e}")

if __name__ == "__main__":
    # Parse arguments
    args = parse_arguments()
    
    # Configure logging
    logging_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=logging_level)
    
    # Load configuration
    config = load_config()
    
    # Start server
    import uvicorn
    
    try:
        uvicorn.run(
            "main:app",
            host=config['api']['host'],
            port=config['api']['port'],
            reload=args.debug,
            log_level="debug" if args.debug else "info"
        )
    except KeyboardInterrupt:
        # Cleanup on shutdown
        asyncio.run(cleanup())
    except Exception as e:
        logger.error(f"Server failed to start: {e}")
        raise
