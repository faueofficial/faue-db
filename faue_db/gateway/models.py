"""gateway schema — identity and all PII. Owned by api-gateway.

Schema: docs/20-services/api-gateway/schema.md
No foreign keys cross schemas; references to ase/media objects are plain UUIDs.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    ARRAY, Boolean, Date, DateTime, ForeignKey, Index, Integer, SmallInteger,
    String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from faue_db.base import Base, TimestampMixin, UUIDPrimaryKey, WorkspaceScopedMixin, uuid7
from faue_db.types import BlindIndex, EncryptedStr

SCHEMA = {"schema": "gateway"}


# --- workspaces (ADR 0021) --------------------------------------------------
class Workspace(Base, UUIDPrimaryKey):
    """Reserved now, single-tenant in behaviour. kind is 'personal' at MVP."""
    __tablename__ = "workspaces"
    __table_args__ = SCHEMA
    kind: Mapped[str] = mapped_column(Text, default="personal", nullable=False)
    name: Mapped[str | None] = mapped_column(Text)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"
    __table_args__ = SCHEMA
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("gateway.workspaces.id", ondelete="CASCADE"),
        primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("gateway.users.id", ondelete="CASCADE"),
        primary_key=True)
    role: Mapped[str] = mapped_column(Text, default="owner", nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# --- identity ---------------------------------------------------------------
class User(Base, UUIDPrimaryKey, TimestampMixin):
    """Not workspace-scoped: a user is a member of workspaces, not owned by one."""
    __tablename__ = "users"
    __table_args__ = SCHEMA
    status: Mapped[str] = mapped_column(Text, default="active", nullable=False)
    age_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuthIdentity(Base, UUIDPrimaryKey):
    """One user, many identities. Linking happens only on a VERIFIED email match —
    unverified auto-linking is an account-takeover path."""
    __tablename__ = "auth_identities"
    __table_args__ = (
        UniqueConstraint("provider", "provider_uid"),
        Index("ix_auth_identities_email_bidx", "email_bidx",
              postgresql_where=None),
        SCHEMA,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("gateway.users.id", ondelete="CASCADE"), nullable=False)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    provider_uid: Mapped[str] = mapped_column(Text, nullable=False)
    email_enc: Mapped[bytes | None] = mapped_column(EncryptedStr)
    email_bidx: Mapped[str | None] = mapped_column(BlindIndex)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    phone_enc: Mapped[bytes | None] = mapped_column(EncryptedStr)
    phone_bidx: Mapped[str | None] = mapped_column(BlindIndex)
    display_name: Mapped[str | None] = mapped_column(Text)  # Apple sends this once only
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RefreshToken(Base, UUIDPrimaryKey):
    __tablename__ = "refresh_tokens"
    __table_args__ = SCHEMA
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("gateway.users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    family_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False, index=True)
    rotated_from: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True))
    # Why the token was revoked. Without this, a normal logout is
    # indistinguishable from token theft and the reuse alert drowns in noise.
    revoked_reason: Mapped[str | None] = mapped_column(Text)  # rotated | logout | family_revoked
    user_agent: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# --- profile ----------------------------------------------------------------
class Profile(Base, WorkspaceScopedMixin, TimestampMixin):
    __tablename__ = "profiles"
    __table_args__ = SCHEMA
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("gateway.users.id", ondelete="CASCADE"),
        primary_key=True)
    username: Mapped[str | None] = mapped_column(String(24), unique=True)
    display_name: Mapped[str | None] = mapped_column(Text)
    gender_presentation: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(Text)
    geohash5: Mapped[str | None] = mapped_column(String(5))  # ~5km; never raw coordinates
    locale: Mapped[str] = mapped_column(Text, default="en-NG", nullable=False)
    currency: Mapped[str] = mapped_column(Text, default="NGN", nullable=False)
    avatar_asset_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True))


class BodyProfile(Base, WorkspaceScopedMixin):
    """The most sensitive table in the system. Never in an event payload, never
    sent raw to a model — ase receives derived silhouette constraints only."""
    __tablename__ = "body_profile"
    __table_args__ = SCHEMA
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("gateway.users.id", ondelete="CASCADE"),
        primary_key=True)
    body_shape: Mapped[str | None] = mapped_column(Text)
    height_cm_enc: Mapped[bytes | None] = mapped_column(EncryptedStr)
    measurements_enc: Mapped[bytes | None] = mapped_column(EncryptedStr)
    fit_preference: Mapped[str | None] = mapped_column(Text)
    sizes_by_category: Mapped[dict | None] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Consent(Base, WorkspaceScopedMixin):
    """Denied by default, always."""
    __tablename__ = "consents"
    __table_args__ = SCHEMA
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("gateway.users.id", ondelete="CASCADE"),
        primary_key=True)
    purpose: Mapped[str] = mapped_column(Text, primary_key=True)
    granted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    policy_version: Mapped[str | None] = mapped_column(Text)
    granted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source: Mapped[str | None] = mapped_column(Text)


class DeletionLedger(Base, UUIDPrimaryKey):
    """No FK on user_id: the user row is deleted while the ledger must survive as
    the compliance record."""
    __tablename__ = "deletion_ledger"
    __table_args__ = SCHEMA
    user_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sla_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    modules_pending: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    modules_done: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list, nullable=False)
    third_parties_done: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# --- style DNA --------------------------------------------------------------
class StylePreferences(Base, WorkspaceScopedMixin):
    __tablename__ = "style_preferences"
    __table_args__ = SCHEMA
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("gateway.users.id", ondelete="CASCADE"),
        primary_key=True)
    dna_scores: Mapped[dict | None] = mapped_column(JSONB)  # raw, not sharpened
    dna_dominant: Mapped[str | None] = mapped_column(String(2))
    dna_alter_ego: Mapped[str | None] = mapped_column(String(2))
    dna_wildcard: Mapped[str | None] = mapped_column(String(2))
    tagline: Mapped[str | None] = mapped_column(Text)
    blend_line: Mapped[str | None] = mapped_column(Text)
    personal_line: Mapped[str | None] = mapped_column(Text)  # M1-2, frozen once generated
    quiz_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    quiz_version: Mapped[str | None] = mapped_column(Text)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retake_available_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class QuizResponse(Base, UUIDPrimaryKey, WorkspaceScopedMixin):
    """Append-only: DNA evolution across retakes stays analysable."""
    __tablename__ = "quiz_responses"
    __table_args__ = SCHEMA
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("gateway.users.id", ondelete="CASCADE"),
        nullable=False, index=True)
    quiz_version: Mapped[str] = mapped_column(Text, nullable=False)
    answers: Mapped[dict] = mapped_column(JSONB, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# --- media (module — extractable) -------------------------------------------
class Asset(Base, UUIDPrimaryKey, WorkspaceScopedMixin):
    """An uploaded image, after the PII pipeline has finished with it.

    Lives in the gateway schema because `media` is an M1-2 extraction; the same
    arrangement as `notify`.

    The per-stage booleans are not bookkeeping. They turn the compliance
    question into a query rather than an argument:

        SELECT count(*) FROM gateway.assets
        WHERE status = 'ready' AND (NOT exif_stripped OR NOT faces_redacted);

    which must always be zero. A pipeline bug becomes visible instead of silent.
    """
    __tablename__ = "assets"
    __table_args__ = SCHEMA
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("gateway.users.id", ondelete="CASCADE"),
        nullable=False, index=True)
    kind: Mapped[str] = mapped_column(Text, nullable=False)      # vault | fabric | avatar
    status: Mapped[str] = mapped_column(Text, nullable=False)    # pending | processing | ready | rejected
    #: Why an image was refused. A closed set, so a spike is groupable.
    rejection_reason: Mapped[str | None] = mapped_column(Text)

    #: Where the derivative lives. The original is never addressable — it is
    #: discarded once the derivative exists.
    storage_key: Mapped[str | None] = mapped_column(Text)
    thumb_key: Mapped[str | None] = mapped_column(Text)
    preview_key: Mapped[str | None] = mapped_column(Text)
    content_type: Mapped[str | None] = mapped_column(Text)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    bytes: Mapped[int | None] = mapped_column(Integer)

    # --- pipeline audit ---
    exif_stripped: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    faces_redacted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    faces_found: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ocr_redacted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    safety_verdict: Mapped[str | None] = mapped_column(Text)
    #: Keeping an original means keeping the unredacted face and the GPS
    #: coordinates. It requires a consent purpose that does not exist yet, so
    #: this stays false and the column is here to make that visible.
    original_retained: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    retention_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    #: When the derivative reached the backup replica.
    #:
    #: Null on a ready asset means the backup is missing it — which is what the
    #: reconciliation worker sweeps for. Replication is deliberately not inline:
    #: a transient backup outage must neither fail an upload nor be swallowed
    #: into a silent gap discovered when the backup is finally needed.
    backed_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# --- vault ------------------------------------------------------------------
class VaultItem(Base, UUIDPrimaryKey, WorkspaceScopedMixin, TimestampMixin):
    """Soft-deletes: wear_log references items historically, and a wear record
    pointing at nothing is worse than a tombstone."""
    __tablename__ = "vault_items"
    __table_args__ = SCHEMA
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("gateway.users.id", ondelete="CASCADE"),
        nullable=False, index=True)
    asset_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    subcategory: Mapped[str | None] = mapped_column(Text)
    colors: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    fabric: Mapped[str | None] = mapped_column(Text)
    brand: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    wear_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_worn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WearLog(Base, UUIDPrimaryKey, WorkspaceScopedMixin):
    __tablename__ = "wear_log"
    __table_args__ = SCHEMA
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("gateway.users.id", ondelete="CASCADE"),
        nullable=False, index=True)
    item_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(PgUUID(as_uuid=True)), nullable=False)
    look_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True))
    occasion: Mapped[str | None] = mapped_column(Text)
    worn_on: Mapped[date] = mapped_column(Date, nullable=False)
    source: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# --- looks and signals ------------------------------------------------------
class SavedLook(Base, UUIDPrimaryKey, WorkspaceScopedMixin):
    """`snapshot` is the one deliberate denormalisation: a saved look must stay
    viewable even if the underlying ase record is pruned."""
    __tablename__ = "saved_looks"
    __table_args__ = (UniqueConstraint("user_id", "look_id"), SCHEMA)
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("gateway.users.id", ondelete="CASCADE"), nullable=False)
    look_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    saved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FeedbackSignal(Base, UUIDPrimaryKey, WorkspaceScopedMixin):
    __tablename__ = "feedback_signals"
    __table_args__ = (UniqueConstraint("user_id", "target_type", "target_id"), SCHEMA)
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("gateway.users.id", ondelete="CASCADE"), nullable=False)
    target_type: Mapped[str] = mapped_column(Text, nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    signal: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ActionEvent(Base, UUIDPrimaryKey, WorkspaceScopedMixin):
    __tablename__ = "action_events"
    __table_args__ = SCHEMA
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("gateway.users.id", ondelete="CASCADE"),
        nullable=False, index=True)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    item_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True))
    brand_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True))
    look_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True))
    surface: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# --- integrations -----------------------------------------------------------
class IntegrationAccount(Base, UUIDPrimaryKey, WorkspaceScopedMixin):
    __tablename__ = "integration_accounts"
    __table_args__ = (UniqueConstraint("user_id", "provider"), SCHEMA)
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("gateway.users.id", ondelete="CASCADE"), nullable=False)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    provider_uid: Mapped[str] = mapped_column(Text, nullable=False)
    access_token_enc: Mapped[bytes] = mapped_column(EncryptedStr, nullable=False)
    refresh_token_enc: Mapped[bytes | None] = mapped_column(EncryptedStr)
    scopes: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(Text, nullable=False)
    sync_cursor: Mapped[dict | None] = mapped_column(JSONB)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# --- notify (module — extractable) ------------------------------------------
class NotifyPreference(Base, WorkspaceScopedMixin):
    __tablename__ = "notify_preferences"
    __table_args__ = SCHEMA
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("gateway.users.id", ondelete="CASCADE"),
        primary_key=True)
    category: Mapped[str] = mapped_column(Text, primary_key=True)
    channel: Mapped[str] = mapped_column(Text, primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    quiet_hours_start: Mapped[int | None] = mapped_column(SmallInteger)
    quiet_hours_end: Mapped[int | None] = mapped_column(SmallInteger)


class NotifyDelivery(Base, UUIDPrimaryKey, WorkspaceScopedMixin):
    """The unique constraint is what makes redelivery safe: a replayed event
    cannot produce a second push.

    `channel` is part of the key because one row *is* one channel. Without it
    the first channel to claim an event locks out every other, so a message
    meant for inbox and email only ever reached whichever ran first — and it
    looked like correct deduplication.
    """
    __tablename__ = "notify_deliveries"
    __table_args__ = (
        UniqueConstraint("user_id", "template_id", "event_id", "channel"),
        SCHEMA,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    template_id: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[str] = mapped_column(Text, nullable=False)
    event_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True))
    status: Mapped[str] = mapped_column(Text, nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class NotifyInbox(Base, UUIDPrimaryKey, WorkspaceScopedMixin):
    __tablename__ = "notify_inbox"
    __table_args__ = SCHEMA
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("gateway.users.id", ondelete="CASCADE"),
        nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    deeplink: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(Text)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class NotifyDevice(Base, UUIDPrimaryKey, WorkspaceScopedMixin):
    __tablename__ = "notify_devices"
    __table_args__ = SCHEMA
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("gateway.users.id", ondelete="CASCADE"), nullable=False)
    platform: Mapped[str] = mapped_column(Text, nullable=False)
    token_enc: Mapped[bytes] = mapped_column(EncryptedStr, nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# --- admin ------------------------------------------------------------------
class AdminUser(Base, UUIDPrimaryKey):
    __tablename__ = "admin_users"
    __table_args__ = SCHEMA
    email_enc: Mapped[bytes] = mapped_column(EncryptedStr, nullable=False)
    email_bidx: Mapped[str] = mapped_column(BlindIndex, unique=True, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    mfa_enrolled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    #: TOTP shared secret, encrypted at rest. Whoever holds this can mint valid
    #: second factors, so it is exactly as sensitive as the account itself.
    totp_secret_enc: Mapped[bytes | None] = mapped_column(EncryptedStr)
    #: Set when enrolment is confirmed with a working code, not when the secret
    #: is issued. An unconfirmed secret means the operator never successfully
    #: scanned it, and treating that as enrolled locks them out permanently.
    mfa_enrolled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(Text, default="active", nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AuditLog(Base, UUIDPrimaryKey):
    """Append-only at the role level. Survives user deletion — it is the artefact
    demonstrating access accountability to a regulator. Retention: 7 years."""
    __tablename__ = "audit_log"
    __table_args__ = SCHEMA
    actor_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False, index=True)
    actor_role: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    target_type: Mapped[str] = mapped_column(Text, nullable=False)
    target_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), index=True)
    before: Mapped[dict | None] = mapped_column(JSONB)
    after: Mapped[dict | None] = mapped_column(JSONB)
    justification: Mapped[str | None] = mapped_column(Text)
    ip: Mapped[str | None] = mapped_column(INET)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# --- outbox -----------------------------------------------------------------
class Outbox(Base, UUIDPrimaryKey):
    """Written in the same transaction as the state change it describes. This is
    what makes 'state saved but event lost' impossible."""
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
