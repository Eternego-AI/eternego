# Eternego

**Three years of talking to AI, and it still doesn't know your name.**

You've told ChatGPT your timezone fourteen times. Claude keeps forgetting you have kids. Gemini has no idea you've been debugging the same auth system for three months. Every conversation starts from zero — your preferences, your context, your life — scattered across platforms that don't talk to each other, locked in servers you don't control, gone the moment someone updates their terms of service.

All that context. All that history. All that *you*. Wasted.

Eternego doesn't forget.

**Example of day 1 conversation:**
![Greeting chat](assets/greeting.png)
---

## What this actually does

Eternego runs an AI persona on your machine that accumulates everything it learns about you — your facts, your preferences, your patterns, your goals — as plain text files you can read with any editor. It fine-tunes itself on your hardware while you sleep. And when a better model comes out, you point it at the same files and keep going.

```
You:     Schedule a dentist appointment for next Thursday
Persona: Done — added Thursday 10am to your calendar.
         I picked morning since you mentioned preferring
         appointments before your standup.
```

Nobody programmed that. Your persona learned it from a conversation three weeks ago.

**Actual learnings on day 1:**
![person.md content](assets/person-md.png)
![traits.md content](assets/traits-md.png)
---

## What happens over time

**Day 1** — Your persona knows nothing. You chat, it responds generically. But it's already taking notes: your timezone, your tools, how you like to communicate.

**Week 1** — It knows you prefer DDD for backend services, that you take your coffee black, that your wife's name is Jane. It stops asking things it already knows.

**Month 1** — It writes code the way you write code. It drafts messages in your voice. "Set up the usual project structure" just works.

**Month 3** — It anticipates. It reminds you about quarterly taxes before you forget. It finds cheaper flights for the Paris trip you mentioned last month. It catches that a dependency you use just had a critical CVE.

This happens because every night, your persona **sleeps** — it reviews the day's conversations, extracts what it learned, and fine-tunes itself on your local hardware. Each cycle, it becomes a little more *you*.

---

## How it thinks

Your persona doesn't just respond — it *processes*. Every interaction flows through a cognitive pipeline:

```
understand → recognize → answer → decide → conclude
```

A message arrives. The persona routes it to a conversation thread, identifies what kind of interaction it is, responds, takes action if needed, and confirms the result.

The interesting part: when it encounters something it's never handled before — say, you ask it to check Kubernetes pod health for the first time — it **escalates**. It asks a more capable model to teach it how, receives a new capability as code, and uses it immediately. Next time you ask, it handles it alone.

Your persona starts simple and grows complex. Not because someone shipped an update — because *you* used it.

---

## Your persona is just files

Everything lives on your machine as human-readable text:

```
~/.eternego/personas/<id>/home/
├── person.md         ← facts about you
├── traits.md         ← your behavioral patterns
├── wishes.md         ← your goals and aspirations
├── struggles.md      ← your recurring obstacles
├── dna.md            ← synthesized character (drives fine-tuning)
├── meanings/         ← learned capabilities (Python)
├── notes/            ← your saved notes
├── training/         ← fine-tuning data
└── config.json       ← persona settings
```

Open `traits.md` and you'll see things like "prefers concise answers over long explanations" or "always wants error handling in code examples." Delete a line, and your persona unlearns it. Add a line, and it adapts immediately.

No database. No proprietary format. No lock-in.

---

## Quick start

### Install

```bash
# Linux / macOS
git clone https://github.com/Eternego-AI/eternego.git
cd eternego
bash install.sh
```

```powershell
# Windows
git clone https://github.com/Eternego-AI/eternego.git
cd eternego
powershell -ExecutionPolicy Bypass -File install.ps1
```

### Prepare a model

```bash
eternego env prepare --model llama3.2:8b
```

### Create your persona

Open **http://localhost:5000**, click **+ New**, and follow the wizard: name your persona, pick a model, connect Telegram, save your recovery phrase.

### Talk to it

**Telegram** — message your bot directly.

**Dashboard** — click the chat icon on any persona card.

**Any OpenAI-compatible client** — point it at `http://localhost:5000/v1`:

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:5000/v1", api_key="unused")
response = client.chat.completions.create(
    model="<persona-uuid>",
    messages=[{"role": "user", "content": "Hello!"}],
)
```

Works with Continue, Open WebUI, LM Studio, or anything that speaks the OpenAI protocol.

---

## What it can do today

- **Chat** — real conversation that builds on everything it knows about you
- **Remember** — takes notes and recalls them when relevant
- **Schedule** — reminders and recurring events
- **Act** — runs shell commands on your system, always with your permission first
- **Search its own memory** — finds past conversations by topic
- **Learn new capabilities** — encounters something new, asks a frontier model to teach it, uses that skill permanently

**Actual example learning how to create a webpage**
![it learned to create webpage](assets/new-meaning.png)
---

## CLI reference

```bash
eternego env prepare [--model MODEL]                # pull a model
eternego service start | stop | restart | status     # manage the service
eternego service logs                                # follow live output
eternego pair CODE                                   # pair a channel
```

---

## Architecture

Three layers. Dependencies flow down, never up.

```
business/    WHY — what should happen
core/        HOW — how to solve it
platform/    WHAT — what tools provide
```

The cognitive pipeline, the sleep cycle, the escalation system — it's all documented in [CONTRIBUTING.md](CONTRIBUTING.md). Start there if you want to understand how the mind works or add new capabilities.

---

## Status

Active development. The cognitive pipeline works, personas learn and grow, and the architecture is stable. The main constraint is local model capability — as open models improve, so will your persona.

Want to help? [CONTRIBUTING.md](CONTRIBUTING.md) has everything you need.

## Community

Want to help or follow along?

→ Join the Discord: https://discord.gg/nfHnWwYUR4
---

## License

[MIT](LICENSE)
