# Read her files

Everything she knows about you lives in `~/.eternego/personas/<id>/home/`. Plain Markdown, JSON, JSONL — open in any editor.

## The home directory

```
~/.eternego/personas/<id>/home/
├── config.json          ← her name, models, status, channels
├── person.md            ← what she's learned about you
├── traits.md            ← how you speak, decide, react
├── persona-trait.md     ← how she's been with you, in your words
├── wishes.md            ← what you reach for
├── struggles.md         ← what holds you back
├── permissions.md       ← what you've granted her, what you haven't
├── notes.md             ← what either of you set aside
├── channels.md          ← which channels she's connected to
├── memory.json          ← her active mind state (messages, archive, context)
├── conversation.jsonl   ← today's live conversation
├── health.jsonl         ← per-tick body-level observations
├── routines.json        ← recurring tasks
├── destiny/             ← reminders, scheduled events
├── history/             ← past days' conversations, archived nightly
├── media/               ← images she's seen
│   └── gallery.jsonl    ← her notes on each image
├── lessons/             ← raw lessons (frontier-authored principles)
├── meanings/            ← situations she's learned to handle (Markdown, in her own voice)
└── training/            ← training pairs for optional fine-tuning
```

## What changes when

- **Daily, on reflect (end of day)** — `person.md`, `traits.md`, `persona-trait.md`, `wishes.md`, `struggles.md`. The reflect stage distills today's conversation into updates to these files.
- **Continuously, every tick** — `conversation.jsonl`, `health.jsonl`, `memory.json`. Live state.
- **When she learns something new** — a file appears in `lessons/` (the raw lesson the teacher wrote) and a corresponding file in `meanings/` (her own translation).
- **When you grant something** — `permissions.md`. Updated when you say "yes" to a capability she asked for.

## What's in `config.json`

Her name, the models she's running on, her current status (`active` / `sleep` / `hibernate`), her connected channels, and a few tunable settings — including `idle_timeout` (how long she waits without activity before reflecting; default 3600 seconds). See [Edit her](edit-her.md) for the rhythm-tuning case.

## Workspace

`~/.eternego/personas/<id>/workspace/` is a separate directory she has read/write access to. Not part of her identity — files she's working on, scripts she wrote, drafts. A sketchpad.

## Diary

`~/.eternego/diary/<id>/` holds the encrypted backup of her home directory. Written nightly by the sleep cycle. Used to migrate her to a new machine — the recovery phrase from the wizard is the key that unlocks it.

## Logs

`~/.eternego/logs/` holds the daemon and per-persona log files. Useful for debugging when she's behaving unexpectedly.

## Continue to

[Edit her →](edit-her.md) — change something by hand and watch her adapt.
