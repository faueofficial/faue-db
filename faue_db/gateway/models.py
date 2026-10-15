"""gateway schema — identity and all PII. Owned by api-gateway.

Schema: docs/20-services/api-gateway/schema.md
No foreign keys cross schemas; references to ase/media objects are plain UUIDs.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    ARRAY, Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, SmallInteger,
    String, Text, UniqueConstraint, func, text,
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
    #: Set when the person restricted processing (`POST /privacy/restrict`). The
    #: account stays usable; optional processing stops until it is lifted.
    restricted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


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
    #: A code sent to the number was entered. SMS and WhatsApp go only to a
    #: verified number, for the same reason email goes only to a verified address.
    phone_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
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
    #: When the data is actually removed. Between the request and this date the
    #: account is only marked, so a deletion made by mistake can be undone.
    #: Null on rows from before the waiting period existed (already purged).
    purge_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    #: The person (or an admin) took the request back inside the waiting period.
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RuntimeSetting(Base):
    """A non-secret value an operator tuned from the admin console.

    Only keys that differ from their default have a row. The closed set of keys,
    their types and their bounds live in code (`app.modules.runtime_config`), so
    a stray row cannot change anything the code does not already allow.
    """
    __tablename__ = "runtime_settings"
    __table_args__ = SCHEMA
    key: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[dict] = mapped_column(JSONB, nullable=False)   # {"v": <number or bool>}
    reason: Mapped[str | None] = mapped_column(Text)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FeatureFlag(Base):
    """A switch an operator can flip without a deploy.

    Only keys that differ from their default are stored; the closed set of keys
    and their defaults live in code (`app.modules.flags`). The row records who
    changed it, when, and why.
    """
    __tablename__ = "feature_flags"
    __table_args__ = SCHEMA
    key: Mapped[str] = mapped_column(Text, primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ShareEvent(Base, UUIDPrimaryKey):
    """Something of FAUE's was shared out: a Style DNA card sent to Stories or as
    a post, a link copied, the native share sheet used, or a shared link opened.

    Anonymous on purpose: no user, no address, no IP. It exists to count, and the
    website can record one before there is an account.
    """
    __tablename__ = "share_events"
    __table_args__ = (Index("ix_share_events_created", "created_at"), SCHEMA)
    #: story | post | link | native | view
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    #: web | app
    surface: Mapped[str] = mapped_column(Text, nullable=False)
    #: Dominant persona id on the card, when known.
    persona: Mapped[str | None] = mapped_column(String(2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SharedItem(Base, UUIDPrimaryKey, WorkspaceScopedMixin):
    """A look someone shared to FAUE: a link from TikTok, Instagram or Pinterest,
    an image, or both.

    Only the link and what its platform publishes for it (author, caption,
    preview address) are kept. `title` and `author_name` are written by strangers
    and are untrusted text. `asset_id` is the cleaned copy that went through the
    PII pipeline, and is what analysis uses.
    """
    __tablename__ = "shared_items"
    __table_args__ = (
        UniqueConstraint("user_id", "source_url"),
        Index("ix_shared_items_user_created", "user_id", "created_at"),
        SCHEMA,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("gateway.users.id", ondelete="CASCADE"), nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)        # tiktok | instagram | pinterest | image
    source_url: Mapped[str | None] = mapped_column(Text)             # canonical; null for an image alone
    title: Mapped[str | None] = mapped_column(Text)
    author_name: Mapped[str | None] = mapped_column(Text)
    thumbnail_url: Mapped[str | None] = mapped_column(Text)
    asset_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("gateway.assets.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(Text, nullable=False)        # ready | needs_image
    reason: Mapped[str | None] = mapped_column(Text)                 # no_preview | unavailable
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DataExport(Base, UUIDPrimaryKey, WorkspaceScopedMixin):
    """A copy of everything held about a person, prepared for them to download.

    `payload` is encrypted: the archive is the most concentrated personal data
    in the system. It expires after seven days and is deleted with the account.
    """
    __tablename__ = "data_exports"
    __table_args__ = (Index("ix_data_exports_user", "user_id"), SCHEMA)
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("gateway.users.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)   # ready | expired
    payload: Mapped[bytes | None] = mapped_column(EncryptedStr)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    downloaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


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
    #: When the stored images were removed (`status` is then `deleted`). The row
    #: stays as a tombstone so records that referenced it keep their shape.
    purged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


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


class ImportedPin(Base, UUIDPrimaryKey, WorkspaceScopedMixin):
    """A pin the user chose to import from a connected account.

    Private to the user and never republished. Deleted with the connection and
    with the account. The title and description are **untrusted text** written by
    strangers: they are kept apart from anything the models are told to do, and
    only ever passed to a model inside a delimited block.

    `asset_id` is the cleaned copy that went through the PII pipeline. It stays
    null, with `image_status = 'pending_detector'`, where no real face and text
    detector exists, so an image is never cached unredacted.
    """
    __tablename__ = "imported_pins"
    __table_args__ = (
        UniqueConstraint("user_id", "provider", "pin_id"),
        Index("ix_imported_pins_user_board", "user_id", "board_id"),
        SCHEMA,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("gateway.users.id", ondelete="CASCADE"), nullable=False)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    board_id: Mapped[str] = mapped_column(Text, nullable=False)
    board_name: Mapped[str] = mapped_column(Text, nullable=False)
    pin_id: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    #: The provider's own CDN address, kept so the image can be cached later.
    image_url: Mapped[str | None] = mapped_column(Text)
    asset_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("gateway.assets.id", ondelete="SET NULL"))
    #: cached | pending_detector | rejected | failed | none
    image_status: Mapped[str] = mapped_column(Text, nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


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
    #: Which delivery this came from, so reading it can mark that delivery opened.
    template_id: Mapped[str | None] = mapped_column(Text)
    event_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True))
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


# --- contact ----------------------------------------------------------------
CONTACT_TOPICS = ("support", "data_request", "press_partnership", "other")
CONTACT_PARTNER_TYPES = (
    "tailor", "designer", "fabric_seller", "event_planner", "stylist_creator", "media", "other",
)
CONTACT_STATUSES = ("new", "replied", "closed")


def _in(values: tuple[str, ...]) -> str:
    return "(" + ", ".join(f"'{v}'" for v in values) + ")"


class ContactMessage(Base, UUIDPrimaryKey):
    """An enquiry sent from the website's contact or partners form.

    Not workspace-scoped: the sender usually has no account. `user_id` is set only
    when a valid session accompanied the request.

    **Retention: 72 hours.** Every personal column (`*_enc`, `*_bidx`) is cleared
    by the purge job three days after `created_at`, and `purged_at` is set. What
    remains is a record that an enquiry existed: reference, topic, status and
    dates. That residue holds nothing that identifies the sender. The privacy
    notice promises this; changing the period means changing both.
    """
    __tablename__ = "contact_messages"
    __table_args__ = (
        CheckConstraint(f"topic IN {_in(CONTACT_TOPICS)}", name="topic"),
        CheckConstraint(f"status IN {_in(CONTACT_STATUSES)}", name="status"),
        CheckConstraint(
            f"partner_type IS NULL OR partner_type IN {_in(CONTACT_PARTNER_TYPES)}",
            name="partner_type"),
        # The purge job scans only rows it has not cleared yet.
        Index("ix_contact_messages_unpurged", "created_at", postgresql_where=text("purged_at IS NULL")),
        SCHEMA,
    )

    #: What the sender is shown and quotes back, e.g. FAUE-7K4M2Q. Not the row id,
    #: so a reference cannot be used to guess or enumerate rows.
    reference: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, default="new", server_default="new", nullable=False)

    # Personal data. Encrypted at rest, and set to NULL when the row is purged.
    name_enc: Mapped[bytes | None] = mapped_column(EncryptedStr)
    email_enc: Mapped[bytes | None] = mapped_column(EncryptedStr)
    #: Lets one person's messages be found for export or erasure without
    #: decrypting every row.
    email_bidx: Mapped[str | None] = mapped_column(BlindIndex, index=True)
    message_enc: Mapped[bytes | None] = mapped_column(EncryptedStr)
    organisation_enc: Mapped[bytes | None] = mapped_column(EncryptedStr)
    role_enc: Mapped[bytes | None] = mapped_column(EncryptedStr)
    #: Keyed hash of the sender's IP, for abuse analysis only. Never the raw address.
    ip_bidx: Mapped[str | None] = mapped_column(BlindIndex)

    partner_type: Mapped[str | None] = mapped_column(Text)
    #: The trace reference the app showed with an error, so support can find the
    #: exact request. An opaque id, not personal data.
    reference_code: Mapped[str | None] = mapped_column(Text)
    user_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True))
    #: The privacy policy version the sender agreed to.
    policy_version: Mapped[str] = mapped_column(Text, nullable=False)
    #: From the Idempotency-Key header. A retry with the same key finds this row
    #: and returns the same reference instead of creating a second message.
    idempotency_key: Mapped[str | None] = mapped_column(Text, unique=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False)
    #: When the FAUE team was emailed about this message.
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    handled_by: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True))
    purged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# --- early access -----------------------------------------------------------
WAITLIST_STATUSES = ("waiting", "invited", "joined", "unsubscribed")
WAITLIST_GENDERS = ("female", "male", "prefer_not_to_say")


class WaitlistEntry(Base, UUIDPrimaryKey):
    """Someone who took the Style DNA quiz on the website and asked to be told
    when FAUE opens.

    Not workspace-scoped: there is no account yet. `user_id` is filled in when the
    same email address later signs up, which is how a waitlist member and their
    account are linked without asking them to prove anything twice.

    The username is a **reservation**, not an account. Nothing here authenticates
    anyone; the sign-up flow checks it so another person cannot take the handle
    someone already asked for.

    Basis: consent, given at the form with the policy version recorded. Kept until
    launch or until the person unsubscribes or asks for deletion.
    """
    __tablename__ = "waitlist_entries"
    __table_args__ = (
        CheckConstraint(f"status IN {_in(WAITLIST_STATUSES)}", name="status"),
        CheckConstraint(f"gender IS NULL OR gender IN {_in(WAITLIST_GENDERS)}", name="gender"),
        SCHEMA,
    )

    email_enc: Mapped[bytes] = mapped_column(EncryptedStr, nullable=False)
    #: One entry per address. Also how a repeat submission is recognised without
    #: decrypting anything.
    email_bidx: Mapped[str] = mapped_column(BlindIndex, unique=True, nullable=False)
    #: As typed, for display.
    username: Mapped[str] = mapped_column(String(24), nullable=False)
    #: Lower-cased. Unique, so `Ada` and `ada` cannot both be reserved.
    username_key: Mapped[str] = mapped_column(String(24), unique=True, nullable=False)

    #: 'female', 'male' or 'prefer_not_to_say', from the dropdown. Used only to
    #: choose the model photograph behind their Style DNA card. NULL for entries made before it
    #: was asked.
    gender: Mapped[str | None] = mapped_column(String(20))

    # The Style DNA they got, so the card can be reproduced and the list can be
    # grouped by style without re-scoring.
    dna_quiz_version: Mapped[str] = mapped_column(Text, nullable=False)
    dna_answers: Mapped[dict] = mapped_column(JSONB, nullable=False)
    dna_scores: Mapped[dict] = mapped_column(JSONB, nullable=False)
    dna_dominant: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    dna_alter_ego: Mapped[str | None] = mapped_column(Text)
    dna_wildcard: Mapped[str | None] = mapped_column(Text)

    status: Mapped[str] = mapped_column(Text, default="waiting", server_default="waiting", nullable=False)
    source: Mapped[str] = mapped_column(Text, default="web_quiz", server_default="web_quiz", nullable=False)
    #: The policy version in force when they agreed to be emailed.
    policy_version: Mapped[str] = mapped_column(Text, nullable=False)
    consented_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True))
    ip_bidx: Mapped[str | None] = mapped_column(BlindIndex)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    #: When the confirmation email went out.
    welcomed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    invited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    unsubscribed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


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


class CommunityPost(Base, UUIDPrimaryKey, WorkspaceScopedMixin):
    """A look its owner chose to show to other people on FAUE.

    Public by the owner's explicit act, and anonymous to readers: nothing in a
    feed response names the person. `title`, `image_url`, `occasion` and `recipe`
    are a snapshot taken from the look when it was published, so the post does not
    change or disappear if the look does. `persona` is the owner's dominant Style
    DNA at the time and is what a feed is ranked by.
    """
    __tablename__ = "community_posts"
    __table_args__ = (
        UniqueConstraint("user_id", "look_id"),
        Index("ix_community_posts_feed", "status", "persona", "created_at"),
        SCHEMA,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("gateway.users.id", ondelete="CASCADE"), nullable=False)
    look_id: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str] = mapped_column(Text, nullable=False)
    occasion: Mapped[str | None] = mapped_column(Text)
    caption: Mapped[str | None] = mapped_column(String(140))
    persona: Mapped[str | None] = mapped_column(String(8))
    recipe: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="published")  # published | removed | hidden
    likes_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    copies_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reports_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CommunityLike(Base, WorkspaceScopedMixin):
    __tablename__ = "community_likes"
    __table_args__ = SCHEMA
    post_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("gateway.community_posts.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("gateway.users.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CommunityCopy(Base, WorkspaceScopedMixin):
    """Someone took a post's recipe as the start of their own look."""
    __tablename__ = "community_copies"
    __table_args__ = SCHEMA
    post_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("gateway.community_posts.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("gateway.users.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CommunityReport(Base, WorkspaceScopedMixin):
    __tablename__ = "community_reports"
    __table_args__ = SCHEMA
    post_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("gateway.community_posts.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("gateway.users.id", ondelete="CASCADE"), primary_key=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


EVENT_KINDS = ("wedding", "owambe", "church", "naming", "work", "travel", "other")
EVENT_REMINDERS = ("none", "1d", "3d", "7d")
NOTE_SOURCES = ("user", "learned")


class UserEvent(Base, UUIDPrimaryKey, WorkspaceScopedMixin):
    """A dated occasion the person wants to dress for. Only the title, day, kind and a city are kept:
    ASE plans looks and weather from those, and nothing is read from a calendar."""
    __tablename__ = "user_events"
    __table_args__ = (
        CheckConstraint(f"kind IN {_in(EVENT_KINDS)}", name="kind"),
        CheckConstraint(f"remind IN {_in(EVENT_REMINDERS)}", name="remind"),
        Index("ix_user_events_user_day", "user_id", "starts_on"),
        SCHEMA,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("gateway.users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(80), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="other")
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    city: Mapped[str | None] = mapped_column(String(60))
    has_fabric: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    remind: Mapped[str] = mapped_column(String(8), nullable=False, default="3d")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Tailor(Base, UUIDPrimaryKey, WorkspaceScopedMixin):
    """A tailor the person sends briefs to. The number is personal data about a third party that the
    owner chose to give us, so it is encrypted, shown only to the owner, and deleted with the account."""
    __tablename__ = "tailors"
    __table_args__ = (Index("ix_tailors_user", "user_id"), SCHEMA)
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("gateway.users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    phone_enc: Mapped[bytes | None] = mapped_column(EncryptedStr)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AseNote(Base, UUIDPrimaryKey, WorkspaceScopedMixin):
    """Something the person told ASE about their taste, in their own words, or something ASE noticed.
    The person can pause or forget any of them; ASE reads only the active ones."""
    __tablename__ = "ase_notes"
    __table_args__ = (
        CheckConstraint(f"source IN {_in(NOTE_SOURCES)}", name="source"),
        Index("ix_ase_notes_user", "user_id", "created_at"),
        SCHEMA,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("gateway.users.id", ondelete="CASCADE"), nullable=False)
    text: Mapped[str] = mapped_column(String(300), nullable=False)
    source: Mapped[str] = mapped_column(String(8), nullable=False, default="user")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
