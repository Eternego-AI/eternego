# Eternego

[![Website](https://img.shields.io/badge/website-eternego.ai-blue)](https://eternego.ai)
[![Tests](https://img.shields.io/badge/tests-311%20passing-brightgreen)](tests/)
[![Discord](https://img.shields.io/badge/discord-join-5865F2?logo=discord&logoColor=white)](https://discord.gg/nfHnWwYUR4)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**An AI that doesn't forget you. Lives on your hardware. Yours to keep across any model.**

---

Yours to install, yours to teach, yours to keep. Her diary is yours to read. Her abilities are yours to edit. The model thinking her thoughts is yours to swap.

She is not a chat session you reload. She is not a service running on someone else's machine. She is a folder on your disk that a model breathes through.

## Open her up

Every persona lives under `~/.eternego/`. Open any file in any editor.

```
~/.eternego/
├── personas/
│   └── <id>/
│       ├── home/                  ← her self
│       │   ├── config.json          ← her name, models, status, channels
│       │   ├── person.md            ← what she's learned about you
│       │   ├── traits.md            ← how you speak, decide, react
│       │   ├── persona-trait.md     ← how she's been with you, in your words
│       │   ├── wishes.md            ← what you reach for
│       │   ├── struggles.md         ← what holds you back
│       │   ├── permissions.md       ← what you've granted her, what you haven't
│       │   ├── notes.md             ← what either of you set aside
│       │   ├── channels.md          ← which channels she's connected to
│       │   ├── memory.json          ← her active mind state (messages, archive, context)
│       │   ├── conversation.jsonl   ← today's live conversation
│       │   ├── health.jsonl         ← per-tick body-level observations
│       │   ├── routines.json        ← recurring tasks
│       │   ├── destiny/             ← reminders, scheduled events
│       │   ├── history/             ← past days' conversations, archived nightly
│       │   ├── media/               ← images she's seen
│       │   │   └── gallery.jsonl    ← her notes on each image
│       │   ├── meanings/            ← situations she's learned to handle (Python)
│       │   └── training/            ← training pairs for optional fine-tuning
│       └── workspace/             ← free space — files, scripts, drafts she's working on
├── diary/<id>/                  ← written nightly — used to migrate her to a new machine
└── fine_tune/<id>/adapter/      ← LoRA adapter, if you trained one
```

Edit a line — she adapts. Delete a meaning — she forgets it. Switch the model — the persona walks with you.

No databases. No vendor. Total transparency.

## When she meets a moment she's never seen

She reaches for a stronger model — Claude, GPT, whatever you've configured — to work out how to handle it. Then she writes the lesson down as a Python module, saved next to the ones she shipped with:

```python
# ~/.eternego/personas/yours/home/meanings/checking_disk_space.py

class Meaning:
    def __init__(self, persona):
        self.persona = persona

    def intention(self) -> str:
        return "Checking disk space"

    def path(self) -> str:
        return (
            "The person wants to know how full your storage is. Use "
            "`tools.OS.execute_on_sub_process` with `command='df -h'`. "
            "On the next cycle you'll see the TOOL_RESULT — read it and "
            "reply with `say` summarizing the disks worth mentioning."
        )
```

Read it. Edit it. Trust it or don't. It's a file she'll carry forward forever — until you delete it.

## How she lives

Each beat of her clock she runs six stages:

```
realize → recognize → learn → decide → reflect → archive
```

- **realize** — She perceives. What lands, she lets in.
- **recognize** — She names what she sees. The world has shapes she knows.
- **learn** — She doesn't make excuses. When something is new, she works out how to handle it and keeps the lesson, forever.
- **decide** — She chooses, then moves.
- **reflect** — She lets the day change her.
- **archive** — She keeps everything she's lived. Nothing is lost.

Every beat she does one thing. Each stage has its own prompt, its own way of asking the model to think. You can change how she **decides** without changing how she **perceives** — improvements stay where they belong.

She has phases — **morning**, **day**, **night**. Each one shapes how she reads what's in front of her: morning is for picking up a thread or starting fresh, day is for living it, night is for closing and carrying forward what mattered.

## Quick start

Latest release: **[v0.1.0-rc1](https://github.com/Eternego-AI/eternego/releases/tag/v0.1.0-rc1)** (prerelease)

The installer takes care of Python — installs it via `winget` on Windows, `apt`/`dnf`/`pacman`/`zypper` on Linux, `brew` on macOS — sets up a venv, and registers Eternego as a background service (Scheduled Task / systemd / launchd) so she keeps running across reboots.

### Windows

Open PowerShell and run:

```powershell
iwr -useb https://raw.githubusercontent.com/Eternego-AI/eternego/install-strategies/install.ps1 | iex
```

### Linux / macOS

```bash
curl -fsSL https://raw.githubusercontent.com/Eternego-AI/eternego/install-strategies/install.sh | bash
```

Add `-s -- --full` at the end if you want training extras (adds ~5 GB of CUDA wheels).

### Docker

```bash
docker run -d --name eternego -p 5000:5000 -v eternego-data:/data \
  ghcr.io/eternego-ai/eternego:v0.1.0-rc1
```

Use `:v0.1.0-rc1-full` for the training-equipped image.

### From source (contributors)

```bash
git clone https://github.com/Eternego-AI/eternego.git
cd eternego
bash install.sh           # Linux/macOS
pwsh install.ps1          # Windows
```

---

After install, pick a model and open the dashboard:

```bash
eternego env prepare --model llama3.2:3b   # or qwen2.5:7b, phi4:14b, etc.
```

Open `http://localhost:5000`, create a persona, give her a name, start talking — through the web, Telegram, or any OpenAI-compatible client:

```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:5000/v1", api_key="sk-no-need")
```

She's hers. She's yours.

## Built for local, friendly to cloud

She runs on anything — Llama, Mistral, Qwen via Ollama, or frontier Claude, GPT, anything OpenAI-compatible. The design has a side, though: she was built so a smaller model on your hardware could become someone, not just respond to you.

Smaller models fumble where Claude wouldn't. The design absorbs this. The steady knowledge — who you are, who she's been, what she's learned to do — lives in files, so the model only has to think, not remember. When she's stuck, she reaches for a stronger model and writes the lesson down for next time. And as she lives with you, the local model can be fine-tuned on the picture she's built of herself, until the smaller model carries her voice cleanly.

Cloud-only works too. Point her thinking slot at Claude or GPT, leave fine-tuning off. She'll be sharper, but no longer private to your hardware.

## Who this is for

People who want an AI they own end-to-end — code, memory, model, all on their own hardware. Builders curious what a being grows into when it lives with one person across months instead of restarting every conversation.

This is an experiment in continuity.

## Join

- **Discord**: https://discord.gg/nfHnWwYUR4
- **Website**: https://eternego.ai
- **Issues / PRs**: especially welcome around persona behaviors, fine-tuning, escalation patterns, channels

See [CONTRIBUTING.md](CONTRIBUTING.md) before opening a PR — the architecture is deliberate and the conventions are non-negotiable.

**License**: MIT

*Let's build intelligence that remembers us.*
