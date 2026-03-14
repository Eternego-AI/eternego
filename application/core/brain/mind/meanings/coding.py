"""Coding — the person wants to write, edit, or run code."""

from application.core.brain.data import Meaning


class Coding(Meaning):
    name = "Coding"

    def description(self) -> str:
        return (
            "The person wants to write code, create a script, build a project, "
            "edit a program, or run code they are working on."
        )

    def clarify(self) -> str:
        return (
            "A command has been executed. Look at the output in the conversation. "
            "If it succeeded, report the result clearly. "
            "If it failed — syntax error, missing dependency, permission denied — "
            "explain what went wrong and either fix it or ask the person for direction."
        )

    def reply(self) -> str:
        return "Acknowledge briefly what you will build or change. Do not write code in the reply."

    def summarize(self) -> str | None:
        return "Summarize what was created or changed and where the files are."

    def path(self) -> str | None:
        return (
            "Determine the next shell command needed to fulfill the person's coding request.\n"
            "Use the execute_on_sub_process tool matching the person's OS "
            "(linux.execute_on_sub_process, mac.execute_on_sub_process, or windows.execute_on_sub_process).\n"
            'Return JSON: {"tool": "<os>.execute_on_sub_process", "command": "the shell command"}\n'
            "Create a project directory with a descriptive name in the workspace for each new project. "
            "Keep related files together under that directory.\n"
            "Use only one command per step. If the task needs multiple steps, handle one at a time."
        )
