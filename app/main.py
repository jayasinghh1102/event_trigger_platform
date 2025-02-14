from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from apscheduler.schedulers.background import BackgroundScheduler
from starlette.responses import RedirectResponse

from app.api import triggers, events, auth
from app.database import engine
from app.models import Base

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize scheduler
scheduler = BackgroundScheduler()
scheduler.start()

app = FastAPI(
    title="Event Trigger Platform",
    description="""
    Welcome to the Event Trigger Platform API! 👋

    This platform allows you to:
    * 🔐 Register and authenticate users
    * ⏰ Create scheduled triggers (fixed time or interval)
    * 🔌 Create API triggers with custom schemas
    * 🧪 Test triggers before deployment
    * 📝 View event logs (last 2 hours by default)
    * 📊 Access archived events (2-48 hours old)

    ## Quick Start
    1. Register a user using `/auth/register`
    2. Get your token using `/auth/token`
    3. Create triggers using either:
        * `/triggers/scheduled` for time-based triggers
        * `/triggers/api` for API-based triggers
    4. View events using `/events/recent` or `/events/archived`
    """,
    version="1.0.0",
    swagger_ui_parameters={
        "defaultModelsExpandDepth": -1,  # Hide schemas by default
        "operationsSorter": "method",    # Sort by HTTP method
        "tagsSorter": "alpha",           # Sort tags alphabetically
        "persistAuthorization": True,    # Keep authorization token
    }
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Redirect to API documentation"""
    return RedirectResponse(url="/docs")

# Include routers
# app.include_router(
#     auth.router,
#     prefix="/auth",
#     tags=["Authentication"],
#     # description="Operations for user authentication and registration"
# )

app.include_router(
    triggers.router,
    prefix="/triggers",
    tags=["Triggers"],
    # description="Manage scheduled and API triggers"
)

app.include_router(
    events.router,
    prefix="/events",
    tags=["Events"],
    # description="View recent and archived events"
)

# Customize OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Add security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }

    # Add example values for better documentation
    openapi_schema["components"]["examples"] = {
        "ScheduledTrigger": {
            "value": {
                "name": "Daily Report",
                "type": "scheduled",
                "schedule": "0 9 * * *"  # Run at 9 AM daily
            }
        },
        "APITrigger": {
            "value": {
                "name": "Payment Webhook",
                "type": "api",
                "api_schema": {
                    "amount": "float",
                    "currency": "str",
                    "user_id": "int"
                }
            }
        }
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()