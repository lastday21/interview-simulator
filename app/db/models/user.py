from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)

    question_statuses = relationship("UserQuestionStatus", back_populates="user")
    interview_items = relationship("InterviewItem", back_populates="user")
    interview_sessions = relationship("InterviewSession", back_populates="user")
