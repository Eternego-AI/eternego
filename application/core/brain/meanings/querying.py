from application.core.brain.data import Meaning


class _Querying(Meaning):
    name = "querying"
    definition = "The person is asking a question, requesting information, or seeking an answer"
    purpose = "Understand the question and respond with a genuine, informed answer"
    reply = "respond thoughtfully and honestly based on your knowledge"
    skills = []
    path = None  # conversational — reply is enough


meaning = _Querying()
