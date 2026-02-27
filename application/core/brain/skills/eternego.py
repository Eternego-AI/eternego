"""Eternego — how Eternego works and how to operate it."""

from application.core.brain.data import Skill


class _EternegoSkill(Skill):
    name = "eternego"
    description = (
        "Explains how Eternego works — the service, dashboard, persona files, "
        "channel pairing, and common troubleshooting."
    )

    def execution(self):
        def _doc(persona):
            from application.core import paths
            storage = str(paths.home(persona.id))
            return f"""# Eternego

Eternego runs AI personas on the person's own hardware. Each persona learns from every interaction and stores its knowledge as plain files.

## Service

```
eternego service status    # is the service running?
eternego service logs      # tail live logs
eternego service start
eternego service stop
eternego service restart
```

## Dashboard

Open in a browser: `http://localhost:8000/dashboard`

- Persona cards with live signal feed
- Persona detail: identity, traits, struggles, skills, history
- Chat UI per persona

## Persona Files

All persona data lives under:

```
{storage}/
  config.json           # persona identity — name, birthday, model, version
  context.md            # evolving operational context
  person.md             # facts about the person (name, role, location)
  traits.md             # how the person prefers to work and communicate
  struggles.md          # recurring obstacles and unmet needs
  permissions.md        # pending and granted permissions
  channels.md           # verified channel chat IDs
  skills/               # loaded skill documents
  workspace/            # sandbox for scripts and temp files
  notes/                # the person's notes
  history/              # long-term conversation history (per topic)
  training/             # LoRA training data
```

## Channel Pairing (Telegram)

When a persona receives a message from an unknown sender, it sends back a pairing code. The person runs this on their machine to verify:

```
eternego pair <code>
```

## Environment

```
eternego env check     # verify Ollama, Git, model availability
eternego env prepare   # install missing dependencies
```

## Multi-step Workflows

When running commands that produce output you need to report (status, logs, env check), use `reflect` with the result so the next tick can compose an accurate response rather than guessing.

## Common Issues

**Persona not responding on Telegram**
- `eternego service status` — is the service running?
- `eternego service logs` — look for errors near the persona name
- Check `channels.md` — is that chat ID listed?

**Model not loading / slow responses**
- `eternego env check` — confirms Ollama is running and the model is pulled

**Persona seems to have forgotten something**
- Check `traits.md` and `person.md`
- Check `history/` — past conversations are archived here after sleep"""
        return _doc


skill = _EternegoSkill()
