"""Celery task queue integration demo."""

import time
from kewe import Blueprint, Request, json
from kewe.errors.exceptions import BadRequest
from celery import Celery
from celery.result import AsyncResult
from database_config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND

celery_bp = Blueprint("celery", url_prefix="/api/celery")

# Initialize Celery
celery_app = Celery(
    "kewe_demo",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,
    task_soft_time_limit=240,
)


# ---- Celery Tasks ----
@celery_app.task(bind=True, name="demo.slow_task")
def slow_task(self, duration: int = 5):
    """Simulate a slow background task."""
    for i in range(duration):
        time.sleep(1)
        self.update_state(state="PROGRESS", meta={"current": i + 1, "total": duration})
    return {"status": "completed", "duration": duration, "result": f"Task ran for {duration} seconds"}


@celery_app.task(bind=True, name="demo.data_processing")
def data_processing_task(self, items: int = 100):
    """Simulate data processing."""
    processed = 0
    for i in range(0, items, 20):
        time.sleep(0.5)
        processed = min(i + 20, items)
        self.update_state(state="PROGRESS", meta={"processed": processed, "total": items})
    return {"status": "completed", "items_processed": processed}


@celery_app.task(bind=True, name="demo.email_notification")
def email_notification_task(self, recipient: str, subject: str, body: str = ""):
    """Simulate sending an email notification."""
    time.sleep(2)
    return {
        "status": "sent",
        "recipient": recipient,
        "subject": subject,
        "simulated": True,
    }


# ---- API Endpoints ----
@celery_bp.get("/")
async def celery_index():
    return json({
        "broker": "Redis @ 127.0.0.1:6379",
        "status": "connected",
        "endpoints": {
            "start_slow_task": "POST /api/celery/task/slow",
            "start_data_task": "POST /api/celery/task/data",
            "start_email_task": "POST /api/celery/task/email",
            "task_status": "GET /api/celery/task/{task_id}",
            "task_result": "GET /api/celery/result/{task_id}",
            "active_tasks": "GET /api/celery/active",
        }
    })


@celery_bp.post("/task/slow")
async def start_slow_task(request: Request):
    """Start a slow background task."""
    body = await request.json
    duration = body.get("duration", 5)
    task = slow_task.delay(duration=duration)
    return json({
        "task_id": task.id,
        "task_name": "demo.slow_task",
        "status": "queued",
        "duration": duration,
    }, status=202)


@celery_bp.post("/task/data")
async def start_data_task(request: Request):
    """Start a data processing task."""
    body = await request.json
    items = body.get("items", 100)
    task = data_processing_task.delay(items=items)
    return json({
        "task_id": task.id,
        "task_name": "demo.data_processing",
        "status": "queued",
        "items": items,
    }, status=202)


@celery_bp.post("/task/email")
async def start_email_task(request: Request):
    """Start an email notification task."""
    body = await request.json
    recipient = body.get("recipient", "demo@kewe.dev")
    subject = body.get("subject", "Test Notification")
    msg_body = body.get("body", "")
    task = email_notification_task.delay(recipient=recipient, subject=subject, body=msg_body)
    return json({
        "task_id": task.id,
        "task_name": "demo.email_notification",
        "status": "queued",
        "recipient": recipient,
    }, status=202)


@celery_bp.get("/task/{task_id:str}")
async def get_task_status(task_id: str):
    """Get Celery task status."""
    result = AsyncResult(task_id, app=celery_app)
    response = {
        "task_id": task_id,
        "status": result.state,
        "ready": result.ready(),
        "successful": result.successful() if result.ready() else None,
    }
    if result.state == "PROGRESS" and result.info:
        response["progress"] = result.info
    if result.ready():
        if result.successful():
            response["result"] = result.get()
        else:
            response["error"] = str(result.info) if result.info else "Unknown error"
    return json(response)


@celery_bp.get("/result/{task_id:str}")
async def get_task_result(task_id: str):
    """Get Celery task result (blocks until ready)."""
    from celery.exceptions import TimeoutError as CeleryTimeout
    result = AsyncResult(task_id, app=celery_app)
    try:
        value = result.get(timeout=10)
        return json({"task_id": task_id, "status": "completed", "result": value})
    except CeleryTimeout:
        return json({"task_id": task_id, "status": "pending", "message": "Task still running"}, status=202)
    except Exception as e:
        return json({"task_id": task_id, "status": "error", "error": str(e)})


@celery_bp.get("/active")
async def get_active_tasks():
    """Get active Celery tasks."""
    try:
        inspect = celery_app.control.inspect()
        active = inspect.active()
        scheduled = inspect.scheduled()
        return json({
            "active": active or {},
            "scheduled": scheduled or {},
        })
    except Exception as e:
        return json({"error": str(e), "note": "Inspect may not work with all broker configurations"})
