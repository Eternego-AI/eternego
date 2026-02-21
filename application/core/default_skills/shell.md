# Shell

Use `act` to run shell commands:

```json
{"act": [{"function": {"name": "shell", "arguments": {"command": "your command here"}}}]}
```

## Workspace

Write all files to: {workspace}

## Common Patterns

| Task | Command |
|---|---|
| Read a file | `cat /path/to/file` |
| List directory | `ls -la /path` |
| Write to workspace | `echo "content" > {workspace}/file.txt` |
| Append to file | `echo "line" >> {workspace}/file.txt` |
| Current date/time | `date` |
| Check if installed | `which command_name` |
| Find files | `find /path -name "*.ext"` |
| Disk usage | `du -sh /path` |
| Running processes | `ps aux | grep name` |

## Caution

Never use shell to directly modify these persona files:

`persona-identity.md`, `persona-context.md`, `person-identity.md`, `person-traits.md`, `permissions.md`

Use the abilities for those instead.
