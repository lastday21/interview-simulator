from aiogram.filters.callback_data import CallbackData


MAIN_MENU = "menu:main"
TRAINER_MENU = "menu:trainer"
INTERVIEW_MENU = "menu:interview"
STATISTICS_MENU = "menu:statistics"
TRAINER_TOPICS = "trainer:topics"


class TrainerTopicCallback(CallbackData, prefix="trainer_topic"):
    topic_id: int


class TrainerSubtopicCallback(CallbackData, prefix="trainer_subtopic"):
    subtopic_id: int
