from aiogram.fsm.state import State, StatesGroup


class TrainerStates(StatesGroup):
    select_topic = State()
    select_subtopic = State()
    questions_list = State()
    wait_question_number = State()
    question = State()


class InterviewStates(StatesGroup):
    menu = State()
    select_topics = State()
    select_subtopics = State()
    active = State()


class StatisticsStates(StatesGroup):
    menu = State()
