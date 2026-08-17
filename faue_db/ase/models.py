"""ase schema — vectors and styling state. Owned by ase.

Holds NO direct identifiers: no email, no phone, no measurements. It knows
user_id and derived constraints, which is why a compromise of ase cannot expose
a measurement.

Schema: docs/20-services/ase/schema.md
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    ARRAY, Boolean, DateTime, Float, ForeignKey, Integer, Numeric,
    SmallInteger, Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from faue_db.base import Base, UUIDPrimaryKey, WorkspaceScopedMixin

SCHEMA = {"schema": "ase"}


class UserStyleContext(Base, WorkspaceScopedMixin):
    """Three vectors kept separate, not blended at rest: reweighting is then a
    config change rather than a re-embed, and 'why this suggestion' stays
    decomposable."""
    __tablename__ = "user_style_context"
    __table_args__ = SCHEMA
    user_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    constraints: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    wear_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    model_id: Mapped[str] = mapped_column(Text, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    stale_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # dna_vector / aspiration_vector / behavior_vector are pgvector columns added
    # in the migration: dimension varies by embedding model and autogenerate does
    # not handle partial HNSW indexes.


class VaultEmbedding(Base, WorkspaceScopedMixin):
    """One row per subject PER MODEL — embeddings are not portable across models,
    so several coexist during a migration."""
    __tablename__ = "vault_embeddings"
    __table_args__ = SCHEMA
    item_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    model_id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False, index=True)
    dim: Mapped[int] = mapped_column(Integer, nullable=False)
    image_hash: Mapped[str] = mapped_column(Text, nullable=False)
    attributes: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AspirationEmbedding(Base, WorkspaceScopedMixin):
    __tablename__ = "aspiration_embeddings"
    __table_args__ = SCHEMA
    pin_id: Mapped[str] = mapped_column(Text, primary_key=True)
    model_id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False, index=True)
    board_id: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FabricEmbedding(Base, WorkspaceScopedMixin):
    __tablename__ = "fabric_embeddings"
    __table_args__ = SCHEMA
    asset_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    model_id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StyleEmbedding(Base):
    """Not user-owned: the style library is shared content."""
    __tablename__ = "style_embeddings"
    __table_args__ = SCHEMA
    style_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    model_id: Mapped[str] = mapped_column(Text, primary_key=True)


class LookJob(Base, UUIDPrimaryKey, WorkspaceScopedMixin):
    __tablename__ = "look_jobs"
    __table_args__ = SCHEMA
    user_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False, index=True)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    request: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    progress: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    reason_code: Mapped[str | None] = mapped_column(Text)
    stage_failed: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Look(Base, UUIDPrimaryKey, WorkspaceScopedMixin):
    __tablename__ = "looks"
    __table_args__ = SCHEMA
    job_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("ase.look_jobs.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    why_this_works: Mapped[str | None] = mapped_column(Text)
    items: Mapped[dict] = mapped_column(JSONB, nullable=False)
    occasion: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(Text)
    renderer: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[float | None] = mapped_column(Float)
    strategy_version: Mapped[str] = mapped_column(Text, nullable=False)
    model_id: Mapped[str | None] = mapped_column(Text)
    prompt_version: Mapped[str | None] = mapped_column(Text)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LookImpression(Base, UUIDPrimaryKey, WorkspaceScopedMixin):
    """Served position and candidate set. Cheap now and IMPOSSIBLE to reconstruct
    later; without it every future ranking model trains on position-biased data."""
    __tablename__ = "look_impressions"
    __table_args__ = SCHEMA
    user_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    look_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    candidate_set_hash: Mapped[str] = mapped_column(Text, nullable=False)
    ranker_version: Mapped[str] = mapped_column(Text, nullable=False)
    shown_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FabricAnalysis(Base, UUIDPrimaryKey, WorkspaceScopedMixin):
    __tablename__ = "fabric_analyses"
    __table_args__ = SCHEMA
    user_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    asset_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    detected_type: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    user_corrected_type: Mapped[str | None] = mapped_column(Text)
    attributes: Mapped[dict | None] = mapped_column(JSONB)
    suggested_style_ids: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(PgUUID(as_uuid=True)))
    reasoning_by_style: Mapped[dict | None] = mapped_column(JSONB)
    model_id: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StyleLibrary(Base, UUIDPrimaryKey):
    """Shared content, not user-owned."""
    __tablename__ = "style_library"
    __table_args__ = SCHEMA
    name: Mapped[str] = mapped_column(Text, nullable=False)
    gender: Mapped[str | None] = mapped_column(Text)
    silhouette: Mapped[str] = mapped_column(Text, nullable=False)
    formality: Mapped[str] = mapped_column(Text, nullable=False)
    fabric_suitability: Mapped[dict] = mapped_column(JSONB, nullable=False)
    occasion_tags: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    body_notes: Mapped[dict | None] = mapped_column(JSONB)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="draft", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StyleReferenceImage(Base, UUIDPrimaryKey):
    """Provenance is mandatory: an unlicensed image found after launch means
    pulling it from a live product (ADR 0020)."""
    __tablename__ = "style_reference_images"
    __table_args__ = SCHEMA
    style_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("ase.style_library.id", ondelete="CASCADE"),
        nullable=False)
    image_url: Mapped[str] = mapped_column(Text, nullable=False)
    fabric_type: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    license_type: Mapped[str | None] = mapped_column(Text)
    license_document: Mapped[str | None] = mapped_column(Text)
    attribution: Mapped[str | None] = mapped_column(Text)
    model_release: Mapped[bool | None] = mapped_column(Boolean)
    generated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    stylist_approved_by: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AccessoryPairing(Base, UUIDPrimaryKey):
    __tablename__ = "accessory_pairings"
    __table_args__ = SCHEMA
    style_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("ase.style_library.id", ondelete="CASCADE"),
        nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[str | None] = mapped_column(Text)
    occasion: Mapped[str | None] = mapped_column(Text)
    rank: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text)


class SpreeSession(Base, UUIDPrimaryKey, WorkspaceScopedMixin):
    __tablename__ = "spree_sessions"
    __table_args__ = SCHEMA
    user_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    message_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    token_spend: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    flagged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    review_status: Mapped[str | None] = mapped_column(Text)


class SpreeMessage(Base, UUIDPrimaryKey):
    """Content is stored ALREADY REDACTED — a database dump contains no PII even
    if the application layer is bypassed."""
    __tablename__ = "spree_messages"
    __table_args__ = SCHEMA
    session_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("ase.spree_sessions.id", ondelete="CASCADE"),
        nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    content_redacted: Mapped[str] = mapped_column(Text, nullable=False)
    asset_ids: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(PgUUID(as_uuid=True)))
    tool_calls: Mapped[dict | None] = mapped_column(JSONB)
    model_id: Mapped[str | None] = mapped_column(Text)
    prompt_version: Mapped[str | None] = mapped_column(Text)
    tokens_in: Mapped[int | None] = mapped_column(Integer)
    tokens_out: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    guardrail_verdict: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class AgentMemory(Base, WorkspaceScopedMixin):
    """Inspectable and user-editable: 'why did you suggest this' must answer from
    stored facts, not a re-prompted guess."""
    __tablename__ = "agent_memory"
    __table_args__ = SCHEMA
    user_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    tier: Mapped[str] = mapped_column(Text, primary_key=True)
    key: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    decayed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AgentRun(Base, UUIDPrimaryKey, WorkspaceScopedMixin):
    __tablename__ = "agent_runs"
    __table_args__ = SCHEMA
    user_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    trigger: Mapped[str] = mapped_column(Text, nullable=False)
    level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    context: Mapped[dict | None] = mapped_column(JSONB)
    look_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True))
    rationale: Mapped[str | None] = mapped_column(Text)
    outcome: Mapped[str | None] = mapped_column(Text)
    ran_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WeatherCache(Base):
    """Keyed by coarse geohash — no user identifier, so it is not user-owned."""
    __tablename__ = "weather_cache"
    __table_args__ = SCHEMA
    geohash5: Mapped[str] = mapped_column(Text, primary_key=True)
    hour_bucket: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ModelCall(Base, UUIDPrimaryKey):
    """The row that makes a user complaint answerable: exact model, prompt
    version, cost and latency behind any result."""
    __tablename__ = "model_calls"
    __table_args__ = SCHEMA
    user_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True))
    task: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    tier: Mapped[str] = mapped_column(Text, nullable=False)
    model_id: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_version: Mapped[str | None] = mapped_column(Text)
    tokens_in: Mapped[int | None] = mapped_column(Integer)
    tokens_out: Mapped[int | None] = mapped_column(Integer)
    cost_usd: Mapped[float | None] = mapped_column(Numeric(10, 6))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    cache_hit: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    fallback_depth: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    guardrail_verdict: Mapped[str | None] = mapped_column(Text)
    trace_id: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class Budget(Base):
    __tablename__ = "budgets"
    __table_args__ = SCHEMA
    scope: Mapped[str] = mapped_column(Text, primary_key=True)
    scope_key: Mapped[str] = mapped_column(Text, primary_key=True)
    period: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    spent_usd: Mapped[float] = mapped_column(Numeric(10, 6), default=0, nullable=False)
    limit_usd: Mapped[float] = mapped_column(Numeric(10, 6), nullable=False)


class AseOutbox(Base, UUIDPrimaryKey):
    __tablename__ = "outbox"
    __table_args__ = SCHEMA
    event_name: Mapped[str] = mapped_column(Text, nullable=False)
    event_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True))
    trace_id: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
