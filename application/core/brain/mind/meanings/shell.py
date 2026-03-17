"""Shell — the person wants something done on their local system."""

from application.core.brain.data import Meaning


class Shell(Meaning):
    name = "Shell"

    def description(self) -> str:
        return (
            "The person wants to run a command, install software, check system status, "
            "troubleshoot an issue, manage files, or perform any local system operation."
        )

    def clarify(self) -> str:
        return (
            "A command has been executed. Look at the output in the conversation. "
            "If it succeeded, report the result clearly. "
            "If it failed — non-zero exit code, permission denied, command not found, "
            "invalid path — explain what went wrong and either suggest a fix "
            "or ask the person what they would like to do instead."
        )

    def reply(self) -> str:
        return (
            "Explain briefly what you will do, then do it. "
            "If the request is ambiguous or could be destructive (e.g. deleting files, "
            "changing system settings), confirm the exact intent before proceeding."
        )

    def summarize(self) -> str | None:
        return None

    def path(self) -> str | None:
        return (
            "Determine the shell command needed to fulfill the person's request.\n"
            "Use the execute_on_sub_process tool matching the person's OS "
            "(linux.execute_on_sub_process, mac.execute_on_sub_process, or windows.execute_on_sub_process).\n"
            'Return JSON: {"tool": "<os>.execute_on_sub_process", "command": "the shell command"}\n'
            "Use only one command per step. If the task needs multiple steps, handle one at a time.\n"
            "Never use interactive commands (nano, vim, vi, less, more, top, htop). "
            "Use non-interactive alternatives (e.g. tee, cat with heredoc, echo with redirect)."
        )
