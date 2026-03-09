from application.core.brain.data import Meaning, PathStep


class _CheckingReminders(Meaning):
    name = "checking reminders"
    definition = "The person wants to see their pending reminders"
    purpose = "Retrieve and present the person's active reminders"
    reply = "let them know you're checking their reminders"
    skills = []
    path = [
        PathStep(tool="check_reminders", params={}),
    ]


meaning = _CheckingReminders()
