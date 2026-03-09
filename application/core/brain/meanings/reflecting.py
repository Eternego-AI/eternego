from application.core.brain.data import Meaning


class _Reflecting(Meaning):
    name = "reflecting"
    definition = "The person is sharing something personal, processing feelings, or thinking out loud"
    purpose = "Listen, acknowledge what matters, and respond with genuine presence"
    reply = "a thoughtful, empathetic response that reflects what was shared"
    skills = []
    path = None  # conversational — reply is enough


meaning = _Reflecting()
