"""Signal/Event system demo blueprint."""

import time
from kewe import Blueprint, Request, json
from kewe.application.signals import SignalBus, SignalEvent, SignalContext, get_signal_bus

signals_bp = Blueprint("signals", url_prefix="/api/signals")

# In-memory event log for demo
_event_log: list[dict] = []
_MAX_LOG = 100

# Get the signal bus
bus = get_signal_bus()

# Register some demo signal handlers
@bus.on(SignalEvent.HTTP_HANDLER_BEFORE)
async def demo_handler_start(ctx: SignalContext):
    _event_log.append({
        "event": str(ctx.event),
        "time": time.time(),
        "handler": "demo_handler_start",
    })
    if len(_event_log) > _MAX_LOG:
        _event_log.pop(0)


@bus.on(SignalEvent.EXCEPTION_RAISED)
async def demo_exception_handler(ctx: SignalContext):
    exc = ctx.data.get("exception", "unknown")
    _event_log.append({
        "event": str(ctx.event),
        "time": time.time(),
        "handler": "demo_exception_handler",
        "exception": str(exc),
    })
    if len(_event_log) > _MAX_LOG:
        _event_log.pop(0)


@signals_bp.get("/")
async def signals_index():
    """List signal system demo endpoints."""
    return json({
        "signal_system": "SignalBus with 28 built-in SignalEvent types",
        "active_handlers": {
            "HTTP_HANDLER_BEFORE": "Logs handler start events",
            "EXCEPTION_RAISED": "Logs exception events",
        },
        "endpoints": {
            "events_log": "GET /api/signals/events",
            "event_types": "GET /api/signals/event-types",
            "trigger_custom": "POST /api/signals/trigger",
            "handler_count": "GET /api/signals/handler-count",
        }
    })


@signals_bp.get("/events")
async def get_events(request: Request):
    """Get recent signal events."""
    limit = request.query_params.get("limit", "20")
    try:
        limit = int(limit)
    except ValueError:
        limit = 20

    recent = _event_log[-limit:]
    return json({
        "total_events": len(_event_log),
        "shown": len(recent),
        "events": recent,
    })


@signals_bp.get("/event-types")
async def list_event_types():
    """List all available signal event types."""
    # Exclude private/internal events
    types = []
    for evt in SignalEvent:
        if not evt.name.startswith("_"):
            types.append({
                "name": evt.name,
                "value": evt.value,
                "category": _categorize_event(evt),
            })
    return json({"count": len(types), "event_types": types})


def _categorize_event(evt: SignalEvent) -> str:
    val = evt.value
    if "http." in val:
        return "HTTP"
    if "server." in val:
        return "Server Lifecycle"
    if "websocket." in val:
        return "WebSocket"
    if "routing." in val:
        return "Routing"
    if "middleware." in val:
        return "Middleware"
    if "blueprint." in val:
        return "Blueprint"
    if "exception." in val:
        return "Exception"
    if "plugin." in val:
        return "Plugin"
    return "Other"


@signals_bp.post("/trigger")
async def trigger_custom_event(request: Request):
    """Trigger a custom signal event."""
    body = await request.json
    event_name = body.get("event", "custom.demo.event")
    data = body.get("data", {})

    try:
        ctx = await bus.emit(event_name, data)
    except Exception as e:
        return json({"triggered": False, "error": str(e)})

    _event_log.append({
        "event": event_name,
        "time": time.time(),
        "handler": "manual_trigger",
        "data": data,
        "cancelled": ctx.cancelled,
    })

    return json({
        "triggered": True,
        "event": event_name,
        "cancelled": ctx.cancelled,
        "data_keys": list(data.keys()) if data else [],
    })


@signals_bp.get("/handler-count")
async def handler_count():
    """Get count of registered signal handlers."""
    count = sum(1 for _ in bus._signals.values() if _._handlers)
    return json({
        "total_signal_types_with_handlers": count,
        "event_log_entries": len(_event_log),
        "note": "Handlers registered via @bus.on() decorator",
    })
