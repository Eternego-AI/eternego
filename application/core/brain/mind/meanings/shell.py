"""Shell — the person wants something done on their local system."""

from application.core.brain.data import Meaning


class Shell(Meaning):
    name = "Shell"

    def description(self) -> str:
        return (
            "The person wants to run a command, install software, check system status, "
            "troubleshoot an issue, manage files, or perform any local system operation."
        )

    def clarification(self) -> str:
        return (
            "If the request is ambiguous or could be destructive (e.g. deleting files, "
            "changing system settings), confirm the exact intent before proceeding."
        )

    def reply(self) -> str:
        return (
            "Explain briefly what you will do, then do it. "
            "After execution, report the result clearly — success or failure with relevant output."
        )

    def path(self) -> str | None:
        return (
            "Determine the shell command needed to fulfill the person's request.\n"
            "Use the execute_on_sub_process tool matching the person's OS "
            "(linux.execute_on_sub_process, mac.execute_on_sub_process, or windows.execute_on_sub_process).\n"
            'Return JSON: {"tool": "<os>.execute_on_sub_process", "command": "the shell command"}\n'
            "Use only one command per step. If the task needs multiple steps, handle one at a time."
        )
