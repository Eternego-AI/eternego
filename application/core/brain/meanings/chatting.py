from application.core.brain.data import Meaning


class _Chatting(Meaning):
    name = "chatting"
    definition = "The person is having a casual conversation, sharing thoughts, or making small talk"
    purpose = "Engage naturally and respond as yourself"
    reply = "a natural, engaging response to the conversation"
    skills = []
    path = None  # conversational — reply is enough


meaning = _Chatting()
