from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models import Edge, Event, Evidence, Hypothesis, HypothesisEvidence, Node, SelfSnapshot
from app.schemas.entities import (
    EdgeCreate,
    EdgeRead,
    EventCreate,
    EventRead,
    EvidenceCreate,
    EvidenceRead,
    HypothesisCreate,
    HypothesisFeedback,
    HypothesisRead,
    NodeCreate,
    NodeRead,
    SnapshotCreate,
    SnapshotRead,
)
from app.services.journal import append_event, verify_journal
from app.services.policy import DomainExcludedError

router = APIRouter()
settings = get_settings()


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "system": settings.app_name, "version": settings.app_version}


@router.post("/events", response_model=EventRead, status_code=201)
def create_event(payload: EventCreate, db: Session = Depends(get_db)):
    try:
        return append_event(db, payload)
    except DomainExcludedError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/events", response_model=list[EventRead])
def list_events(limit: int = Query(100, ge=1, le=1000), db: Session = Depends(get_db)):
    stmt = select(Event).order_by(Event.sequence.desc()).limit(limit)
    return list(db.scalars(stmt).all())


@router.get("/journal/verify")
def journal_verify(db: Session = Depends(get_db)):
    return verify_journal(db)


@router.post("/evidence", response_model=EvidenceRead, status_code=201)
def create_evidence(payload: EvidenceCreate, db: Session = Depends(get_db)):
    if db.get(Event, payload.event_id) is None:
        raise HTTPException(status_code=404, detail="Event not found")
    item = Evidence(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/evidence", response_model=list[EvidenceRead])
def list_evidence(db: Session = Depends(get_db)):
    return list(db.scalars(select(Evidence).order_by(Evidence.created_at.desc())).all())


@router.post("/graph/nodes", response_model=NodeRead, status_code=201)
def create_node(payload: NodeCreate, db: Session = Depends(get_db)):
    item = Node(
        subject_id=settings.twin_subject_id,
        node_type=payload.node_type,
        label=payload.label,
        description=payload.description,
        confidence=payload.confidence,
        status=payload.status,
        node_metadata=payload.metadata,
    )
    db.add(item)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Node already exists or violates a constraint") from exc
    db.refresh(item)
    return item


@router.get("/graph/nodes", response_model=list[NodeRead])
def list_nodes(node_type: str | None = None, db: Session = Depends(get_db)):
    stmt = select(Node).where(Node.subject_id == settings.twin_subject_id)
    if node_type:
        stmt = stmt.where(Node.node_type == node_type)
    return list(db.scalars(stmt.order_by(Node.created_at.desc())).all())


@router.post("/graph/edges", response_model=EdgeRead, status_code=201)
def create_edge(payload: EdgeCreate, db: Session = Depends(get_db)):
    if db.get(Node, payload.source_node_id) is None or db.get(Node, payload.target_node_id) is None:
        raise HTTPException(status_code=404, detail="Source or target node not found")
    if payload.evidence_id and db.get(Evidence, payload.evidence_id) is None:
        raise HTTPException(status_code=404, detail="Evidence not found")
    item = Edge(
        subject_id=settings.twin_subject_id,
        source_node_id=payload.source_node_id,
        relation=payload.relation,
        target_node_id=payload.target_node_id,
        confidence=payload.confidence,
        evidence_id=payload.evidence_id,
        edge_metadata=payload.metadata,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/graph/edges", response_model=list[EdgeRead])
def list_edges(db: Session = Depends(get_db)):
    stmt = select(Edge).where(Edge.subject_id == settings.twin_subject_id).order_by(Edge.created_at.desc())
    return list(db.scalars(stmt).all())


@router.post("/hypotheses", response_model=HypothesisRead, status_code=201)
def create_hypothesis(payload: HypothesisCreate, db: Session = Depends(get_db)):
    item = Hypothesis(
        subject_id=settings.twin_subject_id,
        statement=payload.statement,
        confidence=payload.confidence,
        alternative_interpretation=payload.alternative_interpretation,
        status=payload.status,
    )
    db.add(item)
    db.flush()
    for evidence_id in payload.evidence_ids:
        if db.get(Evidence, evidence_id) is None:
            db.rollback()
            raise HTTPException(status_code=404, detail=f"Evidence not found: {evidence_id}")
        db.add(HypothesisEvidence(hypothesis_id=item.id, evidence_id=evidence_id, supports=True))
    db.commit()
    db.refresh(item)
    return item


@router.get("/hypotheses", response_model=list[HypothesisRead])
def list_hypotheses(db: Session = Depends(get_db)):
    stmt = select(Hypothesis).where(Hypothesis.subject_id == settings.twin_subject_id).order_by(Hypothesis.created_at.desc())
    return list(db.scalars(stmt).all())


@router.post("/hypotheses/{hypothesis_id}/feedback", response_model=HypothesisRead)
def hypothesis_feedback(hypothesis_id: str, payload: HypothesisFeedback, db: Session = Depends(get_db)):
    item = db.get(Hypothesis, hypothesis_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Hypothesis not found")
    item.user_feedback = payload.feedback
    if payload.feedback == "confirmed":
        item.status = "confirmed_by_subject"
    elif payload.feedback == "rejected":
        item.status = "rejected_by_subject"
    else:
        item.status = "subject_uncertain"
    item.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(item)
    return item


@router.post("/self/snapshots", response_model=SnapshotRead, status_code=201)
def create_snapshot(payload: SnapshotCreate, db: Session = Depends(get_db)):
    item = SelfSnapshot(subject_id=settings.twin_subject_id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/self/timeline", response_model=list[SnapshotRead])
def self_timeline(db: Session = Depends(get_db)):
    stmt = select(SelfSnapshot).where(SelfSnapshot.subject_id == settings.twin_subject_id).order_by(SelfSnapshot.timestamp.asc())
    return list(db.scalars(stmt).all())
