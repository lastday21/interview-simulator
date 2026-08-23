from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    SmallInteger,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UserQuestionStatus(Base):
    __tablename__ = "user_question_status"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "question_id", name="uq_user_question_status_user_question"
        ),
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True
    )
    status: Mapped[int] = mapped_column(SmallInteger)
    last_trainer_message_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user = relationship("User", back_populates="question_statuses")
    question = relationship("Question", back_populates="user_statuses")
