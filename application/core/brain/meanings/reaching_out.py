from application.core.brain.data import Meaning, PathStep


class _ReachingOut(Meaning):
    name = "reaching out"
    definition = "The persona needs to proactively contact the person — for a reminder, check-in, or nudge"
    purpose = "Reach out to the person through the active channel"
    reply = None  # silent routine — no immediate reply before reaching out
    skills = []
    path = [
        PathStep(tool="reach_out", params={"text": "a natural, warm message to send to the person"}),
    ]


meaning = _ReachingOut()
