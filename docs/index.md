# Eternego

An AI persona that lives on your hardware, learns from every interaction, and isn't locked to any vendor.

These are the docs — practical guides for installing, running, and extending Eternego. The marketing site is at [eternego.ai](https://eternego.ai); the source is at [github.com/Eternego-AI/eternego](https://github.com/Eternego-AI/eternego).

## Where to start

- **[Getting Started](getting-started/index.md)** — install, create your first persona, learn how to talk to her.
- **[Concepts](concepts/index.md)** — what a persona is, how she thinks, where her knowledge lives.
- **[Build & Extend](build/index.md)** — add tools, abilities, meanings, channels, model providers.
- **[Operating](operating/index.md)** — file layout, logs, troubleshooting, migration.
- **[Reference](reference/index.md)** — data shapes, exception hierarchy, signal types, HTTP API.

## Open her up

Your persona lives in `~/.eternego/`. Open any file, in any editor. No databases. No vendor.

```
~/.eternego/personas/<id>/home/
├── config.json          ← her name, models, status, channels
├── person.md            ← what she's learned about you
├── traits.md            ← how you speak, decide, react
├── persona-trait.md     ← how she's been with you, in your words
├── wishes.md            ← what you reach for
├── struggles.md         ← what holds you back
├── notes.md             ← what either of you set aside
├── permissions.md       ← what you've granted her, what you haven't
├── meanings/            ← situations she's learned to handle
└── ...
```

Edit a line — she adapts. Delete a meaning — she forgets it. Switch the model — she walks with you.
