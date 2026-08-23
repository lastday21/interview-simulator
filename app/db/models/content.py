from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), unique=True)

    subtopics = relationship("Subtopic", back_populates="topic")


class Subtopic(Base):
    __tablename__ = "subtopics"

    id: Mapped[int] = mapped_column(primary_key=True)
    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    position: Mapped[int] = mapped_column()

    topic = relationship("Topic", back_populates="subtopics")
    questions = relationship("Question", back_populates="subtopic")


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str | None] = mapped_column(
        String(64), unique=True, index=True, nullable=True
    )
    source_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    subtopic_id: Mapped[int] = mapped_column(
        ForeignKey("subtopics.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column()
    question_text: Mapped[str] = mapped_column(Text)
    answer_text: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    subtopic = relationship("Subtopic", back_populates="questions")
    user_statuses = relationship("UserQuestionStatus", back_populates="question")
    interview_items = relationship("InterviewItem", back_populates="question")
