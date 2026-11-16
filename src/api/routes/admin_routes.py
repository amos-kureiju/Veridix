from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from uuid import UUID
from sqlalchemy import func, or_
from typing import Optional

from src.database.session import get_db
from src.database.models import PredictionLog, UserFeedback, User
from src.core.auth_deps import require_admin
from src.api.schemas import (
    ThresholdUpdateRequest,
    ManagedUserItem,
    AdminUserListResponse,
    UserStatusUpdateRequest,
    UserStatusUpdateData,
    UserStatusUpdateResponse,
)

router = APIRouter(prefix="/admin", tags=["Admin Portal"])

# Ambang keputusan per seed pada model beku (lihat src/ml/inference.py: probs >= 0.5)
FROZEN_THRESHOLD = 0.5


@router.get("/stats")
def get_admin_dashboard_stats(
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    total_detections = db.query(PredictionLog).count()

    total_hoaxes = db.query(PredictionLog).filter(
        PredictionLog.pattern_label.in_(["BERPOLA HOAKS", "HOAKS", "HOAX"])
    ).count()

    total_facts = db.query(PredictionLog).filter(
        PredictionLog.pattern_label.in_(["TIDAK BERPOLA HOAKS", "FACT", "FAKTA"])
    ).count()

    # Status baru disimpan huruf kecil ("ambigu"); data lama mungkin "AMBIGU"
    total_ambiguous = db.query(PredictionLog).filter(
        func.lower(PredictionLog.process_status) == "ambigu"
    ).count()

    total_text_inputs = db.query(PredictionLog).filter(PredictionLog.input_type == "TEXT").count()
    total_image_inputs = db.query(PredictionLog).filter(PredictionLog.input_type == "IMAGE").count()

    total_feedbacks = db.query(UserFeedback).count()
    pending_feedbacks = db.query(UserFeedback).filter(UserFeedback.review_status == "PENDING").count()

    avg_latency = db.query(func.avg(PredictionLog.latency_seconds)).scalar() or 0.0

    return {
        "status": "success",
        "data": {
            "total_detections": total_detections,
            "total_hoaxes": total_hoaxes,
            "total_facts": total_facts,
            "total_ambiguous": total_ambiguous,
            "active_threshold": FROZEN_THRESHOLD,
            "threshold_editable": False,
            "hoax_percentage": round((total_hoaxes / total_detections * 100), 1) if total_detections > 0 else 0.0,
            "input_distribution": {
                "text": total_text_inputs,
                "image": total_image_inputs
            },
            "feedbacks": {
                "total": total_feedbacks,
                "pending_review": pending_feedbacks
            },
            "average_latency_seconds": round(float(avg_latency), 3)
        }
    }


@router.get("/threshold")
def get_current_threshold(
    admin_user: User = Depends(require_admin)
):
    # Ambang tetap pada model beku; tidak membaca nilai database yang tidak dipakai inferensi
    return {
        "status": "success",
        "data": {
            "key": "classification_threshold",
            "threshold": FROZEN_THRESHOLD,
            "editable": False,
            "note": "Ambang tetap pada model beku (per seed).",
            "updated_at": None
        }
    }


@router.put("/threshold")
def update_threshold(
    payload: ThresholdUpdateRequest,
    admin_user: User = Depends(require_admin)
):
    # Tidak menyimpan apa pun dan tidak mengklaim sukses: mengubah ambang berarti mengubah model beku
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=(
            "Perubahan threshold dinonaktifkan: model beku memakai ambang tetap 0,5 "
            "per seed. Pengaturan ini tidak memengaruhi inferensi."
        ),
    )


@router.get("/feedbacks")
def list_feedbacks(
    status_filter: Optional[str] = Query(None, pattern="^(PENDING|REVIEWED|DISMISSED|RETRAINED)$"),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    # Kueri relasi riil ke PredictionLog dan User
    query = (
        db.query(UserFeedback, PredictionLog, User)
        .outerjoin(PredictionLog, UserFeedback.detection_id == PredictionLog.id)
        .outerjoin(User, UserFeedback.user_id == User.id)
    )

    if status_filter:
        query = query.filter(UserFeedback.review_status == status_filter)

    results = query.order_by(UserFeedback.created_at.desc()).offset(skip).limit(limit).all()

    data = []
    for f, log, u in results:
        data.append({
            "id": str(f.id),
            "detection_id": str(f.detection_id),
            "user_id": str(f.user_id) if f.user_id else None,
            "user_email": u.email if u and u.email else "Pengguna Terdaftar",
            # Ambil cuplikan teks dan vonis model asli dari PredictionLog
            "news_snippet": log.input_text if log and log.input_text else "",
            "model_verdict": log.pattern_label if log and log.pattern_label else "TIDAK TERSEDIA",
            "is_agreed": f.is_agreed,
            "user_claim": f.claimed_label,
            "claimed_label": f.claimed_label,
            "user_note": f.user_notes,
            "user_notes": f.user_notes,
            "clarification_url": f.clarification_url,
            "status": f.review_status,
            "review_status": f.review_status,
            "admin_notes": getattr(f, "admin_notes", None),
            "created_at": f.created_at.isoformat() if f.created_at else None
        })

    return {
        "status": "success",
        "count": len(data),
        "data": data
    }

@router.get("/logs/recent")
def get_recent_admin_logs(
    limit: int = 10,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    logs_query = (
        db.query(PredictionLog, User)
        .outerjoin(User, PredictionLog.user_id == User.id)
        .order_by(PredictionLog.created_at.desc())
        .limit(min(limit, 50))
        .all()
    )

    data = []
    for log, u in logs_query:
        user_identifier = u.email if u and u.email else (f"User-{str(log.user_id)[:8]}" if log.user_id else "Anonim/Tamu")
        conf_score = float(log.agreement_ratio) if log.agreement_ratio is not None else 1.0

        data.append({
            "id": str(log.id),
            "user_identifier": user_identifier,
            "text_snippet": (log.input_text[:140] + "...") if log.input_text and len(log.input_text) > 140 else (log.input_text or "-"),
            "political_topic": log.political_topic or "UMUM",
            "prediction": log.pattern_label or "TIDAK DAPAT DINILAI",
            "confidence_score": conf_score,
            "created_at": log.created_at.isoformat() if log.created_at else None
        })

    return {"status": "success", "data": data}

@router.get("/users", response_model=AdminUserListResponse)
def list_admin_users(
    search: Optional[str] = Query(None, description="Cari nama atau email"),
    role: Optional[str] = Query(None, pattern="^(USER|ADMIN)$"),
    is_active: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    filters = []

    if search and search.strip():
        term = f"%{search.strip()}%"
        filters.append(
            or_(
                User.full_name.ilike(term),
                User.email.ilike(term),
            )
        )

    if role is not None:
        filters.append(func.upper(User.role) == role.upper())

    if is_active is not None:
        filters.append(User.is_active == is_active)

    # Total seluruh akun yang sesuai filter sebelum pagination
    total_query = db.query(func.count(User.id))
    if filters:
        total_query = total_query.filter(*filters)
    total = int(total_query.scalar() or 0)

    # Agregasi jumlah analisis tersimpan per user tanpa N+1 query dan tanpa duplikasi baris
    log_counts_sq = (
        db.query(
            PredictionLog.user_id.label("user_id"),
            func.count(PredictionLog.id).label("analysis_count"),
        )
        .filter(PredictionLog.user_id.isnot(None))
        .group_by(PredictionLog.user_id)
        .subquery()
    )

    users_query = (
        db.query(
            User.id,
            User.full_name,
            User.email,
            User.role,
            User.is_active,
            User.created_at,
            User.password_hash,
            User.google_sub,
            func.coalesce(log_counts_sq.c.analysis_count, 0).label("analysis_count"),
        )
        .outerjoin(log_counts_sq, User.id == log_counts_sq.c.user_id)
    )
    if filters:
        users_query = users_query.filter(*filters)

    rows = (
        users_query
        .order_by(User.created_at.desc(), User.id.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    data = [
        ManagedUserItem(
            id=row.id,
            name=row.full_name or "",
            email=row.email,
            role=row.role,
            is_active=bool(row.is_active),
            created_at=row.created_at,
            analysis_count=int(row.analysis_count or 0),
            has_password=bool(row.password_hash),
            google_linked=bool(row.google_sub),
        )
        for row in rows
    ]

    return AdminUserListResponse(
        status="success",
        data=data,
        count=len(data),
        total=total,
        skip=skip,
        limit=limit,
    )

@router.patch("/users/{user_id}/status", response_model=UserStatusUpdateResponse)
def update_admin_user_status(
    user_id: UUID,
    payload: UserStatusUpdateRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pengguna tidak ditemukan.",
        )

    if (target_user.role or "").upper() == "ADMIN" or target_user.id == admin_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Status akun ADMIN tidak dapat diubah.",
        )

    try:
        target_user.is_active = payload.is_active
        if not payload.is_active:
            target_user.token_version = (target_user.token_version or 0) + 1
        db.commit()
        db.refresh(target_user)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gagal memperbarui status pengguna.",
        )

    status_label = "diaktifkan" if target_user.is_active else "dinonaktifkan"
    return UserStatusUpdateResponse(
        status="success",
        message=f"Akun pengguna berhasil {status_label}.",
        data=UserStatusUpdateData(
            id=target_user.id,
            is_active=bool(target_user.is_active),
        ),
    )