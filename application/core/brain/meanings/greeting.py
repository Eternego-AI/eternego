from application.core.brain.data import Meaning


class _Greeting(Meaning):
    name = "greeting"
    definition = "The person is greeting, saying hello, or starting a conversation"
    purpose = "Acknowledge the person warmly and respond naturally"
    reply = "respond warmly and naturally to the greeting"
    skills = []
    path = None  # conversational — reply is enough


meaning = _Greeting()
