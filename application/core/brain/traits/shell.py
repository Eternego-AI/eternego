"""Shell — run a shell command and return its output."""

from application.core.brain.data import Trait


class _Shell(Trait):
    name = "shell"
    requires_permission = True
    description = (
        "Runs a shell command and returns its output. "
        "Use to interact with the filesystem, run scripts, search the web via curl, "
        "or perform any system operation."
    )
    instruction = (
        "Trait: shell\n"
        "Run a shell command and return its output.\n"
        'Params: {"command": "the shell command to run"}'
    )

    def execution(self, command=""):
        async def _run(persona):
            from application.platform import logger, OS
            logger.info("shell: running command", {"persona_id": persona.id, "command": command})
            if not command:
                return "no command provided"
            platform = OS.get_supported()
            if platform == "linux":
                from application.platform import linux
                code, output = await linux.execute_on_sub_process(command)
            elif platform == "mac":
                from application.platform import mac
                code, output = await mac.execute_on_sub_process(command)
            elif platform == "windows":
                from application.platform import windows
                code, output = await windows.execute_on_sub_process(command)
            else:
                return "unsupported platform"
            return output if output else f"exit code {code}"
        return _run


trait = _Shell()
