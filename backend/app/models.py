import uuid
from datetime import datetime

from sqlalchemy import Computed, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class Investigation(Base):
    """One RCA investigation. `form_data` is the canonical editable form (JSONB);
    `provenance` records per-field AI/human metadata. A few columns are denormalised
    from the form so the list page and the recurrence search stay cheap."""

    __tablename__ = "investigations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    rca_number: Mapped[str] = mapped_column(String(32), unique=True)
    title: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(24), default="draft")  # draft | in_review | approved | closed
    product: Mapped[str] = mapped_column(Text, default="")
    batch_numbers: Mapped[list] = mapped_column(JSONB, default=list)
    equipment_tags: Mapped[list] = mapped_column(JSONB, default=list)
    classification: Mapped[str] = mapped_column(String(16), default="")
    event_type: Mapped[str] = mapped_column(String(64), default="")
    root_cause_summary: Mapped[str] = mapped_column(Text, default="")
    capa_count: Mapped[int] = mapped_column(Integer, default=0)
    form_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    provenance: Mapped[dict] = mapped_column(JSONB, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    search_text: Mapped[str] = mapped_column(Text, default="")
    search_vector = mapped_column(
        TSVECTOR, Computed("to_tsvector('english', coalesce(search_text, ''))", persisted=True)
    )

    documents: Mapped[list["SourceDocument"]] = relationship(back_populates="investigation", cascade="all, delete-orphan")

    __table_args__ = (Index("ix_inv_search_vector", "search_vector", postgresql_using="gin"),)


class SourceDocument(Base):
    __tablename__ = "source_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    investigation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("investigations.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(16))  # pdf | email | text | docx
    sha256: Mapped[str] = mapped_column(String(64))
    pages: Mapped[int] = mapped_column(Integer, default=1)
    text: Mapped[str] = mapped_column(Text, default="")
    meta: Mapped[dict] = mapped_column(JSONB, default=dict)  # email headers, scanned flag, warnings
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    investigation: Mapped[Investigation] = relationship(back_populates="documents")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    investigation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("investigations.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(12))  # user | assistant
    content: Mapped[str] = mapped_column(Text)
    attachments: Mapped[list] = mapped_column(JSONB, default=list)
    meta: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AiRun(Base):
    """Provenance of every LangGraph run: intent, models, prompt version, steps, usage, errors."""

    __tablename__ = "ai_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    investigation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("investigations.id", ondelete="CASCADE"), index=True)
    intent: Mapped[str] = mapped_column(String(24))
    prompt_version: Mapped[str] = mapped_column(String(32))
    llm_mode: Mapped[str] = mapped_column(String(12), default="live")
    steps: Mapped[list] = mapped_column(JSONB, default=list)
    usage: Mapped[dict] = mapped_column(JSONB, default=dict)
    errors: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    investigation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("investigations.id", ondelete="CASCADE"), index=True)
    actor: Mapped[str] = mapped_column(String(80))
    role: Mapped[str] = mapped_column(String(24))
    action: Mapped[str] = mapped_column(String(32))  # ai_applied | user_edit | confirm | submit | approve | create
    path: Mapped[str] = mapped_column(Text, default="")
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
