from aiogram.filters.callback_data import CallbackData


MAIN_MENU = "menu:main"
TRAINER_MENU = "menu:trainer"
INTERVIEW_MENU = "menu:interview"
STATISTICS_MENU = "menu:statistics"
TRAINER_TOPICS = "trainer:topics"
TRAINER_SUBTOPICS = "trainer:subtopics"
TRAINER_START_BEGIN = "trainer:start_begin"
TRAINER_SELECT_NUMBER = "trainer:select_number"
TRAINER_REVIEW_WEAK = "trainer:review_weak"
INTERVIEW_TOPICS = "interview:topics"
INTERVIEW_SUBTOPICS = "interview:subtopics"
INTERVIEW_SELECT_ALL_TOPICS = "interview:select_all_topics"
INTERVIEW_START = "interview:start"
INTERVIEW_RESET_ACTIVE = "interview:reset_active"
INTERVIEW_KEEP_ACTIVE = "interview:keep_active"
INTERVIEW_NEW_SELECTION = "interview:new_selection"


class TrainerTopicCallback(CallbackData, prefix="trainer_topic"):
    topic_id: int


class TrainerSubtopicCallback(CallbackData, prefix="trainer_subtopic"):
    subtopic_id: int


class TrainerQuestionAnswerCallback(CallbackData, prefix="trainer_answer"):
    question_id: int
    status: int


class TrainerQuestionAnswerTextCallback(CallbackData, prefix="trainer_answer_text"):
    question_id: int


class InterviewTopicCallback(CallbackData, prefix="interview_topic"):
    topic_id: int


class InterviewSubtopicCallback(CallbackData, prefix="interview_subtopic"):
    subtopic_id: int


class InterviewAnswerCallback(CallbackData, prefix="interview_answer"):
    question_id: int
    status: int
