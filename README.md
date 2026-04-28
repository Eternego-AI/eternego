# Eternego

[![Release](https://img.shields.io/github/v/release/Eternego-AI/eternego?include_prereleases&sort=semver)](https://github.com/Eternego-AI/eternego/releases)
[![Website](https://img.shields.io/badge/website-eternego.ai-blue)](https://eternego.ai)
[![Tests](https://img.shields.io/badge/tests-313%20passing-brightgreen)](tests/)
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

## Install

Latest release: **[v0.1.0-rc1](https://github.com/Eternego-AI/eternego/releases/tag/v0.1.0-rc1)** (prerelease)

Pick the installer for your machine. Builds aren't code-signed yet, so each OS will warn the first time — instructions for getting past the warning are inline below.

### macOS (.dmg)

Download **[Eternego-v0.1.0-rc1.dmg](https://github.com/Eternego-AI/eternego/releases/download/v0.1.0-rc1/Eternego-v0.1.0-rc1.dmg)**. Open it, drag **Eternego** to **Applications**, then double-click Eternego from Applications.

The first launch shows: *"Eternego.app cannot be opened because the developer cannot be verified."*  Right-click (or Control-click) the app, choose **Open**, then **Open** again in the dialog. macOS remembers the choice — subsequent launches are normal.

### Windows (.exe installer)

Download **[Eternego-v0.1.0-rc1-setup.exe](https://github.com/Eternego-AI/eternego/releases/download/v0.1.0-rc1/Eternego-v0.1.0-rc1-setup.exe)**. Double-click it, walk through the wizard (Next → Install → Finish). Eternego launches automatically and adds Start Menu and Desktop shortcuts.

The wizard's first dialog is *"Windows protected your PC"* (SmartScreen). Click **More info**, then **Run anyway**. SmartScreen remembers this app afterwards.

### Linux (.AppImage)

Download **[Eternego-v0.1.0-rc1-x86_64.AppImage](https://github.com/Eternego-AI/eternego/releases/download/v0.1.0-rc1/Eternego-v0.1.0-rc1-x86_64.AppImage)**, make it executable, run it:

```bash
chmod +x Eternego-v0.1.0-rc1-x86_64.AppImage
./Eternego-v0.1.0-rc1-x86_64.AppImage
```

A single self-contained binary. No system Python needed.

### Docker

The image ships with the persona's own desktop baked in (Xvfb + fluxbox + noVNC). She lives in there; she'll install Firefox or anything else she needs herself when you ask. You can peek at what she's doing at `http://localhost:6080/vnc.html`.

```bash
docker run -d --name eternego --network=host \
  -v eternego-data:/data \
  ghcr.io/eternego-ai/eternego:latest
```

`--network=host` lets the container reach Ollama running natively on your machine (`localhost:11434`). Without it, set `-e OLLAMA_HOST=http://host.docker.internal:11434` and add `-p 5000:5000 -p 6080:6080`.

For an everything-in-containers setup with Ollama as a sibling service, grab the compose file:

```bash
curl -fsSL https://raw.githubusercontent.com/Eternego-AI/eternego/install-strategies/installation/docker/docker-compose.yml > eternego.compose.yml
# edit ports, GPU access, etc. inline; comments explain each line
docker compose -f eternego.compose.yml up -d
```

Use the `:full` tag (or `image: ghcr.io/eternego-ai/eternego:full` in the compose file) for the training-equipped image — adds ~5.5 GB of CUDA wheels for LoRA fine-tuning.

### Background service install (CLI, auto-start on boot)

The installers above launch Eternego when you open them. If you want her to register as a system service so she keeps running across reboots, run this from a terminal instead:

```bash
# Linux (systemd) / macOS (launchd) — auto-installs Python and Ollama via apt/dnf/pacman/brew
curl -fsSL https://raw.githubusercontent.com/Eternego-AI/eternego/install-strategies/installation/install.sh | bash
```

```powershell
# Windows (Scheduled Task) — auto-installs Python via winget
iwr -useb https://raw.githubusercontent.com/Eternego-AI/eternego/install-strategies/installation/install.ps1 | iex
```

Both scripts also accept `--full` (or `-Full` on Windows) to install training extras.

### From source (contributors)

```bash
git clone https://github.com/Eternego-AI/eternego.git
cd eternego
bash installation/install.sh        # Linux/macOS
pwsh installation/install.ps1       # Windows
```

See [CONTRIBUTING.md](CONTRIBUTING.md) before sending a PR.

---

After install, your browser opens to **http://localhost:5000**. The setup form asks for:

- **A name** for your persona.
- **A thinking model** — pick **Cloud (Claude / GPT)** and paste an API key for the easiest path, or **Local (Ollama)** if you want everything to stay on your machine. The local path needs Ollama installed; the installer scripts above install it for you, the .dmg/.exe/.AppImage do not — grab it from [ollama.com](https://ollama.com) first if you're going local.
- **Channels** (optional) — Telegram or Discord tokens to talk to her there too.

Then she comes online. From any tool that speaks OpenAI:

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
