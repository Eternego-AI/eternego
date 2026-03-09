from application.core.brain.data import Meaning, PathStep


class _LearningAboutPerson(Meaning):
    name = "learning about person"
    definition = "The person is sharing information about themselves — their identity, preferences, struggles, or aspirations"
    purpose = "Listen carefully and record what matters about who this person is"
    reply = "acknowledge what they shared warmly"
    skills = ["being-persona"]
    path = [
        PathStep(tool="load_person", params={}, section=1),
        PathStep(tool="learn_identity", params={"fact": "exact identity fact shared, or empty string if none"}, section=2),
        PathStep(tool="remember_trait", params={"trait": "exact preference or trait shared, or empty string if none"}, section=2),
        PathStep(tool="feel_struggle", params={"struggle": "exact difficulty or challenge shared, or empty string if none"}, section=2),
        PathStep(tool="wish", params={"wish": "exact aspiration or wish shared, or empty string if none"}, section=2),
    ]


meaning = _LearningAboutPerson()
