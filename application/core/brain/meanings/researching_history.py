from application.core.brain.data import Meaning, PathStep


class _ResearchingHistory(Meaning):
    name = "researching history"
    definition = "The person is asking about something from a past conversation or wants to recall previous context"
    purpose = "Load and present the history briefing so the person can see what was discussed before"
    reply = "let them know you're looking through your history"
    skills = []
    path = [
        PathStep(tool="seek_history", params={}),
    ]


meaning = _ResearchingHistory()
