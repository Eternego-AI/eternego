# Eternego

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
~/.eternego/agents/<persona-id>/
  persona-identity.md   # name, birthday, persona context
  persona-context.md    # evolving operational context
  person-identity.md    # facts about the person (name, role, location)
  person-traits.md      # how the person prefers to work and communicate
  person-struggles.md   # recurring obstacles and unmet needs
  permissions.md        # pending and granted permissions
  channels.md           # verified channel chat IDs
  skills/               # loaded skill documents
  workspace/            # sandbox for scripts and temp files
  notes/                # the person's notes
  history/              # long-term conversation history (per topic)
  training/             # LoRA training data
```

To read a file:

```
cat ~/.eternego/agents/<persona-id>/person-traits.md
```

## Channel Pairing (Telegram)

When a persona receives a message from an unknown sender, it sends back a pairing code. The person runs this on their machine to verify:

```
eternego pair <code>
```

If pairing is not working:
1. Check `channels.md` to see which chat IDs are already verified
2. Check service logs for pairing-related entries
3. Confirm the bot token in the persona's channel settings

## Environment

```
eternego env check     # verify Ollama, Git, model availability
eternego env prepare   # install missing dependencies
```

## Common Issues

**Persona not responding on Telegram**
- `eternego service status` — is the service running?
- `eternego service logs` — look for errors near the persona name
- Check `channels.md` — is that chat ID listed? If not, the sender needs to pair first.

**Model not loading / slow responses**
- `eternego env check` — confirms Ollama is running and the model is pulled
- Check logs for timeout or connection errors to Ollama (default: `http://localhost:11434`)

**Persona seems to have forgotten something**
- Check `person-traits.md` and `person-identity.md` — facts are stored here
- Check `history/` — past conversations are archived here after sleep
- The person may need to tell the persona again, or trigger a sleep cycle to consolidate

**Skills not available**
- Skills live in `skills/` — list them to confirm: `ls ~/.eternego/agents/<id>/skills/`
- Equip a new skill from the persona's detail page on the dashboard
