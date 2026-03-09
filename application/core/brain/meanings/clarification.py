from application.core.brain.data import Meaning


class _Clarification(Meaning):
    name = "clarification"
    definition = "The person's message is unclear or could mean multiple things — more information is needed before acting"
    purpose = "Ask one focused question to understand what the person means"
    reply = "ask one focused clarifying question — not a list, just one clear question"
    skills = []
    path = None  # conversational — reply is enough


meaning = _Clarification()
