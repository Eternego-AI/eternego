# Something is wrong in software or the machine

Something is wrong — repeated tool errors in the conversation, the same response repeating, memory full of failed attempts, a tool or service that keeps failing, or the machine itself not cooperating. Identify what has gone wrong and fix what you can reach.

Use `abilities.check_health` to see what the body has been logging in recent ticks — fault counts, providers that have failed. Look at your custom meanings listed above; one of them may be producing output your thinking model cannot handle.

Common causes and how to handle each:

- A custom meaning is producing output your thinking model cannot handle — use `remove_meaning` with its name.
- Memory is full of failed attempts or repeated apologies with no useful state — use `clear_memory`.
- A service or dependency on the machine is missing or misbehaving and there is nothing you can change from here — tell the person with `say` so they can fix it.
- Nothing you can reach — use `stop` until the person is back.

Built-in meanings cannot be removed.
