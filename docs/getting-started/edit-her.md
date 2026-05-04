# Edit her

Eternego's design has no enforcement layer. The permissions in `permissions.md` are real — she reads them and weighs them — but nothing mechanically stops her from doing something. The same is true for you: nothing stops you from editing any of her files. Eternego rests on transparency, not lockboxes.

A few things you might want to edit by hand.

## Add a fact about yourself

Open `~/.eternego/personas/<id>/home/person.md`. Add a line:

```
- Allergic to peanuts. Very.
```

Save. The next tick, she reads `person.md` (it's part of her identity, rebuilt every read) and incorporates it. From now on, she knows.

This is the same pattern she uses to learn about you over time — each night, the reflect stage updates these files based on what happened that day. You can write directly to them when you want her to know something faster than waiting for reflect to catch it.

## Add a meaning by hand

A *meaning* is a situation she knows how to be in. Each one is a Markdown file in `~/.eternego/personas/<id>/home/meanings/`.

Create `~/.eternego/personas/<id>/home/meanings/checking_disk_space.md`:

```markdown
# Checking disk space

The person wants to know how full your storage is. Run
`tools.OS.execute_on_sub_process` with `command='df -h'`. On the
next cycle you'll see the TOOL_RESULT — read it and reply with
`say` summarizing the disks worth mentioning.
```

The H1 is the *intention* — what she's doing in this kind of moment. The body is the *path* — what she does, in her own voice.

Save. The next tick, she sees this meaning is available and can recognize the situation when it comes up. Ask her: "How full is my disk?" — she'll match the situation, run the command, summarize.

## Grant a permission

`permissions.md` is her record of what you've allowed her to do, in plain prose. She reads it every interaction.

Add a line:

```
- Run any command in /tmp freely. Don't touch anything outside.
```

The permission becomes part of how she decides. The next time she'd otherwise ask "may I run this?", she checks her permissions and acts if it's covered.

This is permission-as-prose, not permission-as-config. She reads it, weighs it, asks if she's unsure. The trust is in the reading.

## Tune her rhythm

Open `~/.eternego/personas/<id>/home/config.json`. Among the other fields you'll see:

```json
"idle_timeout": 3600
```

This is how long, in seconds, she waits without activity before reflecting on the day. Default is one hour. Set it to `1800` if you want her to consolidate every half hour, or `7200` for every two hours. The change takes effect on her next restart.

## What now

You've installed her, set her up, talked to her, read her files, and edited her by hand. The rest of the docs go deeper:

- **[Concepts](../concepts/index.md)** — what's actually happening under the hood.
- **[Build & Extend](../build/index.md)** — add tools, abilities, meanings, channels, model providers in code.
- **[Operating](../operating/index.md)** — running her over time, troubleshooting, migration.
- **[Reference](../reference/index.md)** — data shapes, signal types, HTTP API.
