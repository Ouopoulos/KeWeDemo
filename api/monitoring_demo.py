"""Monitoring demo: anomaly detection, audit logging, liveness/readiness checks."""

import time
from kewe import Blueprint, Request, json
from kewe.errors.exceptions import BadRequest
from kewe.monitoring.anomaly_detector import AnomalyDetector, SecurityEvent
from kewe.monitoring.audit_log_persistence import (
    AuditLogManager, InMemoryAuditLogStorage, AuditLogEntry
)

monitoring_bp = Blueprint("monitoring", url_prefix="/api/monitoring")

# Anomaly detector
anomaly_detector = AnomalyDetector(max_events=100, time_window=3600)

# Audit log manager (in-memory storage)
audit_storage = InMemoryAuditLogStorage(max_logs=1000)
audit_mgr = AuditLogManager(audit_storage)


# ---- Anomaly Detection ----
@monitoring_bp.get("/anomaly/status")
async def anomaly_status():
    """Get anomaly detection status."""
    return json({
        "detector": "AnomalyDetector",
        "max_events": anomaly_detector.max_events,
        "time_window_seconds": anomaly_detector.time_window,
        "tracked_users": len(anomaly_detector.user_events),
        "tracked_ips": len(anomaly_detector.ip_events),
    })


@monitoring_bp.post("/anomaly/simulate")
async def simulate_event(request: Request):
    """Simulate security events for anomaly detection."""
    body = await request.json
    user_id = body.get("user_id", "test-user")
    ip = body.get("ip", "127.0.0.1")
    event_type = body.get("event_type", "LOGIN_ATTEMPT")
    count = body.get("count", 1)

    anomalies = []
    for i in range(count):
        event = SecurityEvent(
            user_id=user_id,
            event_type=event_type,
            ip_address=ip,
            device_fingerprint=f"device-{user_id}",
            timestamp=time.time(),
            details={"attempt": i + 1, "simulated": True},
        )
        anomaly_detector.add_event(event)

    # Check for anomalies using the detector's all-in-one method
    detected = anomaly_detector.detect_all_anomalies(
        user_id=user_id,
        event_type=event_type,
        ip_address=ip,
        device_fingerprint=f"device-{user_id}",
    )
    if detected:
        for a in detected:
            anomalies.append({"type": a.type or "unknown", "detail": a.detail or str(a)})

    return json({
        "simulated_events": count,
        "user_id": user_id,
        "ip": ip,
        "anomalies_detected": len(anomalies),
        "anomalies": anomalies,
    })


# ---- Audit Logging ----
@monitoring_bp.post("/audit/log")
async def log_audit_event(request: Request):
    """Log an audit event."""
    body = await request.json
    event_type = body.get("event_type", "CUSTOM_EVENT")
    user_id = body.get("user_id", "anonymous")
    details = body.get("details", {})

    audit_mgr.log_security_event(
        event_type=event_type,
        user_id=user_id,
        ip_address=request.headers.get("X-Forwarded-For", "127.0.0.1"),
        details=details,
    )

    return json({
        "logged": True,
        "event_type": event_type,
        "user_id": user_id,
        "total_logs": len(audit_storage.logs),
    })


@monitoring_bp.post("/audit/token-issued")
async def log_token_issued(request: Request):
    """Log a token issuance event."""
    body = await request.json
    user_id = body.get("user_id", "unknown")
    jti = body.get("jti", "unknown")

    audit_mgr.log_token_issued(
        user_id=user_id,
        jti=jti,
        ip_address=request.headers.get("X-Forwarded-For", "127.0.0.1"),
    )

    return json({"logged": True, "event": "TOKEN_ISSUED", "user_id": user_id})


@monitoring_bp.get("/audit/logs")
async def get_audit_logs(request: Request):
    """Get recent audit logs."""
    limit = request.query_params.get("limit", "20")
    try:
        limit = int(limit)
    except ValueError:
        limit = 20

    logs = list(audit_storage.logs)[-limit:]
    result = []
    for entry in logs:
        result.append({
            "timestamp": entry.timestamp,
            "event_type": entry.event_type,
            "user_id": entry.user_id,
            "ip_address": entry.ip_address,
            "details": entry.details,
        })
    return json({
        "total_logs": len(audit_storage.logs),
        "shown": len(result),
        "logs": result,
    })


@monitoring_bp.get("/audit/stats")
async def audit_stats():
    """Get audit log statistics."""
    event_counts = {}
    for entry in audit_storage.logs:
        event_counts[entry.event_type] = event_counts.get(entry.event_type, 0) + 1

    return json({
        "total_logs": len(audit_storage.logs),
        "max_capacity": audit_storage.logs.maxlen,
        "event_type_distribution": event_counts,
    })


# ---- Liveness / Readiness Checks ----
_ready = True
_startup_time = time.time()


@monitoring_bp.get("/live")
async def liveness_check():
    """Liveness probe — is the application running?"""
    return json({"status": "alive", "uptime_seconds": time.time() - _startup_time})


@monitoring_bp.get("/ready")
async def readiness_check():
    """Readiness probe — is the application ready to serve requests?"""
    return json({
        "status": "ready" if _ready else "not_ready",
        "checks": {
            "audit_log": audit_storage is not None,
            "anomaly_detector": anomaly_detector is not None,
        }
    })


@monitoring_bp.post("/ready/toggle")
async def toggle_readiness(request: Request):
    """Toggle readiness status (for testing)."""
    global _ready
    _ready = not _ready
    return json({"ready": _ready, "message": f"Readiness toggled to {_ready}"})
