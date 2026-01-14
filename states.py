from aiogram.fsm.state import StatesGroup, State

class AddPollState(StatesGroup):
    waiting_for_question = State()
    waiting_for_options = State()

class EditPollState(StatesGroup):
    waiting_for_poll_id = State()
    waiting_for_question = State()
    waiting_for_options = State()

class DeletePollState(StatesGroup):
    waiting_for_poll_id = State()
