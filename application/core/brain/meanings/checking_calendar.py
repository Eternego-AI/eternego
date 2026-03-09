from application.core.brain.data import Meaning, PathStep


class _CheckingCalendar(Meaning):
    name = "checking calendar"
    definition = "The person wants to see their upcoming scheduled events or appointments"
    purpose = "Retrieve and present the person's scheduled events"
    reply = "let them know you're checking their calendar"
    skills = []
    path = [
        PathStep(tool="calendar", params={}),
    ]


meaning = _CheckingCalendar()
