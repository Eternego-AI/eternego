from application.core.brain.data import Meaning, PathStep


class _SettingReminder(Meaning):
    name = "setting reminder"
    definition = "The person wants to be reminded of something at a specific date and time"
    purpose = "Create a reminder in the person's destiny and confirm it"
    reply = "confirm the reminder has been set"
    skills = []
    path = [
        PathStep(tool="remind", params={
            "trigger": "date and time in YYYY-MM-DD HH:MM format",
            "timezone": "IANA timezone string (e.g. America/New_York)",
            "content": "what to remind the person about",
        }),
    ]


meaning = _SettingReminder()
