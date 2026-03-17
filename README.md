# Eternego — The Eternal I

Your AI that learns to be you.

Eternego creates an AI persona that lives on your hardware, learns from every conversation, and belongs to no one but you. Everything it knows is stored as plain text files — readable, editable, portable. Switch models whenever you want. Your persona's knowledge stays.

---

## Why Eternego

Today's AI assistants forget you the moment the conversation ends. Your preferences, your context, your history — locked inside someone else's servers, tied to someone else's model.

Eternego is different:

- **It remembers.** Every conversation teaches it who you are — your timezone, your habits, your struggles, your goals. It stores this as human-readable markdown files on your machine.
- **It grows.** When your persona sleeps, it consolidates what it learned, synthesizes its understanding of you, and fine-tunes itself on your local hardware.
- **It's yours.** No cloud dependency. No vendor lock-in. The persona's knowledge works with any model — upgrade when better ones come out, and everything carries over.
- **It thinks.** Not just chat. Your persona has a cognitive pipeline that understands what you need, recognizes the right action, executes it, and confirms — like a real assistant that follows through.

---

## Getting Started

### 1. Install

```bash
# Linux / macOS
bash install.sh
```

```powershell
# Windows (PowerShell)
powershell -ExecutionPolicy Bypass -File install.ps1
```

This installs Python if needed, sets up the `eternego` command, and registers a background service.

The installer starts the service automatically and shows the dashboard URL when done.

### 2. Prepare a model

```bash
eternego env prepare --model llama3.2
```

Pulls the model so your persona can use it. Run once per model.

### 3. Create your persona

Open **http://localhost:5000** and click **+ New**. The wizard walks you through:

1. Name your persona
2. Pick a base model
3. Enter your Telegram bot token
4. Optionally configure a frontier model for escalation
5. Save your recovery phrase
6. Pair your Telegram channel

### 4. Other ways to talk

**Dashboard chat** — click the chat icon on any persona card.

**OpenAI-compatible API** — use any OpenAI client pointed at `http://localhost:5000/v1` with the persona's UUID as the model:

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:5000/v1", api_key="unused")
response = client.chat.completions.create(
    model="<persona-uuid>",
    messages=[{"role": "user", "content": "Hello!"}],
)
print(response.choices[0].message.content)
```

Works with Continue, Open WebUI, LM Studio, or anything that speaks the OpenAI protocol.

---

## What Your Persona Can Do

Out of the box, your persona can:

- **Chat** — genuine conversation, not just Q&A
- **Remember** — take notes and recall them later
- **Schedule** — set reminders and events with recurrence
- **Act** — run shell commands on your system
- **Look back** — search its own conversation history
- **Learn new skills** — when it encounters something it doesn't know how to handle, it asks a frontier model to teach it a new capability, then uses that capability from then on

Everything it learns about you — your facts, your traits, your wishes, your struggles — lives as editable files in `~/.eternego/personas/<id>/home/`.

---

## How It Works

Your persona has a **mind** — a cognitive pipeline that processes every interaction through five stages:

```
understand → recognize → answer → decide → conclude
```

1. **Understand** — incoming messages are routed to conversation threads
2. **Recognize** — each thread is matched to a *meaning* (what kind of interaction is this?)
3. **Answer** — the persona responds to the person
4. **Decide** — structured data is extracted and actions are taken
5. **Conclude** — results are confirmed and the thread is wrapped up

When no existing meaning matches, the persona **escalates** — it asks a more capable model to generate a new meaning as code, learns it, and uses it immediately. Over time, your persona accumulates abilities specific to your life.

Between conversations, the persona **sleeps**: it consolidates what it learned, updates its understanding of you, generates training data, and fine-tunes itself on your hardware. Each sleep cycle makes it a little more *you*.

---

## CLI Reference

```bash
# Environment
eternego env prepare [--model MODEL]    # install dependencies, pull model
eternego env check --model MODEL        # verify model is available

# Service
eternego service start                  # start background service
eternego service stop                   # stop it
eternego service restart                # restart it
eternego service status                 # show status
eternego service logs                   # follow live output

# Channels
eternego pair CODE                      # pair a channel using 6-character code
```

---

## Project Status

Eternego is in active development. The architecture is stable, the cognitive pipeline works, and personas can learn and grow. The main limitation today is local model capability — small models struggle with structured reasoning tasks. As local models improve, so will your persona.

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for architecture details and how to get involved.

---

## License

[MIT](LICENSE)
