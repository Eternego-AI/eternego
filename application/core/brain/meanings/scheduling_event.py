from application.core.brain.data import Meaning, PathStep


class _SchedulingEvent(Meaning):
    name = "scheduling event"
    definition = "The person wants to schedule an appointment, meeting, or event at a specific time"
    purpose = "Record the event in the person's destiny and confirm it"
    reply = "confirm the event has been scheduled"
    skills = []
    path = [
        PathStep(tool="schedule", params={
            "trigger": "event date and time in YYYY-MM-DD HH:MM format",
            "timezone": "IANA timezone string (e.g. America/New_York)",
            "content": "event description",
        }),
    ]


meaning = _SchedulingEvent()
