from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, SmallInteger, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class InterviewItem(Base):
    __tablename__ = "interview_items"
    __table_args__ = (
        UniqueConstraint("user_id", "position", name="uq_interview_items_user_position"),
        UniqueConstraint("user_id", "question_id", name="uq_interview_items_user_question"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column()
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), index=True)
    answer_status: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="interview_items")
    question = relationship("Question", back_populates="interview_items")


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    correct_count: Mapped[int] = mapped_column()
    passed: Mapped[bool] = mapped_column(nullable=False)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user = relationship("User", back_populates="interview_sessions")
