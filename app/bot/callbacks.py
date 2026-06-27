from aiogram.filters.callback_data import CallbackData


MAIN_MENU = "menu:main"
TRAINER_MENU = "menu:trainer"
INTERVIEW_MENU = "menu:interview"
STATISTICS_MENU = "menu:statistics"
TRAINER_TOPICS = "trainer:topics"
TRAINER_START_BEGIN = "trainer:start_begin"
TRAINER_SELECT_NUMBER = "trainer:select_number"


class TrainerTopicCallback(CallbackData, prefix="trainer_topic"):
    topic_id: int


class TrainerSubtopicCallback(CallbackData, prefix="trainer_subtopic"):
    subtopic_id: int


class TrainerQuestionAnswerCallback(CallbackData, prefix="trainer_answer"):
    question_id: int
    status: int


class TrainerQuestionAnswerTextCallback(CallbackData, prefix="trainer_answer_text"):
    question_id: int
