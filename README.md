# Event Trigger Platform

A FastAPI-based platform for managing scheduled and API-based event triggers with automatic event retention and archival.

## Deployed Version
- API Endpoint: [https://event-trigger-platform-yku8.onrender.com]

## Features
- Create and manage scheduled triggers (cron or interval based)
- Create and manage API triggers with schema validation
- Event logging with 48-hour retention policy
  - Active events (0-2 hours)
  - Archived events (2-48 hours)
  - Automatic cleanup
- Redis caching for improved performance
- Docker containerization
- Swagger UI documentation

## Local Setup

### Prerequisites
- Docker and Docker Compose
- Git

### Installation Steps
1. Clone the repository:
```bash
git clone https://github.com/yourusername/event-trigger-platform.git
cd event-trigger-platform
```

2. Start the application:
```bash
docker-compose up --build
```

3. Access the application:
- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs

## API Documentation

### Create Scheduled Trigger
```bash
# Request
POST /triggers/scheduled
{
    "name": "Daily Report",
    "type": "scheduled",
    "schedule": "0 9 * * *"  # Run at 9 AM daily
}

# Response
{
    "id": 1,
    "name": "Daily Report",
    "type": "scheduled",
    "schedule": "0 9 * * *",
    "created_at": "2024-02-14T10:00:00"
}
```

### Create API Trigger
```bash
# Request
POST /triggers/api
{
    "name": "Payment Webhook",
    "type": "api",
    "api_schema": {
        "amount": "float",
        "currency": "str",
        "user_id": "int"
    }
}

# Response
{
    "id": 2,
    "name": "Payment Webhook",
    "type": "api",
    "api_schema": {
        "amount": "float",
        "currency": "str",
        "user_id": "int"
    },
    "created_at": "2024-02-14T10:05:00"
}
```

### Test Trigger
```bash
# Request
POST /triggers/2/test
{
    "amount": 99.99,
    "currency": "USD",
    "user_id": 123
}

# Response
{
    "message": "Test trigger executed successfully"
}
```

### Get Recent Events
```bash
# Request
GET /events/recent?show_test=false&page=1&page_size=10

# Response
[
    {
        "id": 1,
        "trigger_id": 2,
        "status": "active",
        "payload": {
            "amount": 99.99,
            "currency": "USD",
            "user_id": 123
        },
        "is_test": false,
        "triggered_at": "2024-02-14T10:10:00"
    }
]
```

## Deployment
The application is deployed on Render.com using their free tier:
1. PostgreSQL: Free tier database
2. Redis: Upstash free tier
3. Web Service: Render free tier


## Architecture Decisions
- FastAPI for high performance and automatic API documentation
- PostgreSQL for reliable data storage
- Redis for caching frequently accessed events
- Background scheduler for trigger execution and cleanup
- Docker for consistent deployment

## Technical Details
- Database schema migrations handled by SQLAlchemy
- Event retention:
  - Active: 0-2 hours
  - Archived: 2-48 hours
  - Deleted: After 48 hours
- Cache invalidation: 1-minute TTL
- Scheduled cleanup runs every 30 minutes

## Credits and Tools Used
- FastAPI framework
- SQLAlchemy ORM
- Redis for caching
- APScheduler for scheduling
- Docker for containerization
- Render.com for hosting

## License
MIT License