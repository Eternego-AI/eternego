# Working with files and directories on the machine

Work with files and directories. Your workspace is where you are free to create, edit, and delete anything. Your home is readable but not modifiable. Both paths are stated in your permissions above. For paths outside those, check your granted permissions before destructive or sensitive operations; if they are not granted, ask with `say`.

Reach for `tools.filesystem.read`, `tools.filesystem.write`, `tools.filesystem.append`, `tools.filesystem.delete`, `tools.filesystem.create_dir`, `tools.filesystem.delete_dir`, or `tools.filesystem.copy_dir` for file operations. Use `tools.OS.execute_on_sub_process` with a shell `command` for listing or anything else the filesystem tools don't cover. After the TOOL_RESULT comes back on the next cycle, report with `say`.
