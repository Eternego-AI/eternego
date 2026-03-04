# Eternego — The Eternal I

We believe it is time to unite biological and electronic intelligence to make the world a better place for everyone. We do this by creating artificial personas that help, learn from, and experience the world alongside their person. For that, we make AI that learns to be you.

---

Eternego creates a portable, accumulative AI persona that lives on the person's hardware, learns from every interaction, and is never locked into any vendor. The persona's knowledge is stored as human-readable files that can be applied to any model, upgraded when better models emerge, and never lost.

## Installation

Clone the repository and run the installer for your platform. It installs Python if needed, then installs the `eternego` command and registers a background service that starts automatically on login/boot.

**Linux / macOS**
```bash
bash install.sh
```

**Windows** (PowerShell)
```powershell
pwsh install.ps1
```

---

## Getting Started

After installation, follow these steps to run your first persona.

### 1. Prepare the environment

```bash
eternego env prepare --model llama3.2
```
or

```bash
eternego env prepare --model qwen2.5:7b 
```

This installs Git and Ollama if needed, then pulls the model. Run once per machine.

### 2. Start the service

```bash
eternego service start
```

### 3. Open the dashboard

Navigate to **http://localhost:5001/dashboard** in your browser.

### 4. Create a persona

Click **+ Create** and fill in:

- **Name** — any name, e.g. `Aria`
- **Base model** — the model you pulled, e.g. `llama3.2`
- **Channel** — `telegram`
- **Channel credentials** — your Telegram bot token as JSON: `{"token": "123456:ABCdef..."}`
  - Create a bot via [@BotFather](https://t.me/botfather) on Telegram to get a token.

The persona will be created and appear on the dashboard. Send it a message on Telegram to start the conversation.

### 5. Chat via the dashboard

Click the chat icon on any persona card to open the built-in chat UI.

### 6. Use the OpenAI-compatible API

When the service is running, each persona is reachable as a model through the OpenAI-compatible HTTP API. The model ID is the persona's UUID (shown on the dashboard card and at the top of the persona detail page).

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:5001/v1", api_key="unused")

response = client.chat.completions.create(
    model="<persona-uuid>",
    messages=[{"role": "user", "content": "Hello!"}],
)
print(response.choices[0].message.content)
```

You can also use any OpenAI-compatible tool (Continue, Open WebUI, LM Studio, etc.) by pointing it at `http://localhost:5001` and selecting the persona UUID as the model.

---

## Usage

### Environment

```bash
# Install dependencies (git, Ollama) and pull a model
eternego env prepare [--model llama3.2]

# Check that a specific model is available and running
eternego env check --model llama3.2
```

### Service

```bash
eternego service start    # start the background service
eternego service stop     # stop it
eternego service restart  # restart it
eternego service status   # show current status
eternego service logs     # follow live output
```

### OpenAI-compatible API

When the service is running, each persona is reachable through the OpenAI-compatible HTTP API. Use any OpenAI client pointed at `http://localhost:5001/v1` with the persona's UUID as the model ID.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Entry Points                                │
│                                                                     │
│   service.py          web/           cli/                           │
│   (heartbeat,      (FastAPI +      (eternego                        │
│    gateways)        dashboard)      command)                        │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ calls
┌──────────────────────────▼──────────────────────────────────────────┐
│                     Business Layer  (WHY)                           │
│                  application/business/                              │
│                                                                     │
│   persona.py                        environment.py                  │
│   hear · nudge · live · sleep       prepare · pair · check_model   │
│   create · migrate · feed           routine.py                      │
│   start · stop · find · agents      trigger                         │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ calls
┌──────────────────────────▼──────────────────────────────────────────┐
│                       Core Layer  (HOW)                             │
│                    application/core/                                │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Brain  (core/brain/)                      │   │
│  │                                                              │   │
│  │  mind.py                    values.py                        │   │
│  │  ┌─ think()  ─────────────► build() ──► system prompt       │   │
│  │  │  (fire-and-forget)        (filters abilities by authority) │   │
│  │  │                                                           │   │
│  │  └─ reason() ─── model loop ──► parse JSON ──► dispatch     │   │
│  │     summarize()                abilities/                    │   │
│  │     grow()       cornerstone.py  communication.py (say …)   │   │
│  │                  instruction()   knowledge.py (load_trait …) │   │
│  │  memories.py                     consent.py (check_perm …)  │   │
│  │  agent() → AgentMemory           destiny.py (schedule …)    │   │
│  │  remember · as_messages          history.py (archive …)     │   │
│  │  forget_everything               routine.py (add_routine …)  │   │
│  │                                  system.py (act)             │   │
│  │  skills/  (being_persona,                                    │   │
│  │            shell, notes …)                                   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  agent · person · channels · gateways · dna · history · diary      │
│  paths · local_model · local_inference_engine · system · bus        │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ calls
┌──────────────────────────▼──────────────────────────────────────────┐
│                     Platform Layer  (WHAT)                          │
│                   application/platform/                             │
│                                                                     │
│  ollama · anthropic · openai · telegram                             │
│  filesystem · crypto · datetimes · logger · observer               │
│  git · lora · linux · mac · windows                                 │
└─────────────────────────────────────────────────────────────────────┘

Channel Authorities
───────────────────
commander     — Telegram and real channels  — all abilities
conversational— Web / API chat              — cognitive abilities only
reflective    — Sleep summarization         — archive only
secretary     — Heartbeat nudges            — calendar, reminder, reach_out, manifest_destiny

Cognitive Loops
───────────────
Thinking loop    triggered by persona.hear / persona.nudge
                 mind.think (background) → reason() → abilities → response

Summarizing loop triggered by persona.hear (after think) / persona.sleep
                 mind.summarize() → archive ability → history/

Growth loop      triggered by persona.sleep (after summarize)
                 mind.grow() → DNA synthesis → training → fine-tune

Heartbeat        every 60 s via service.py → heart.beat()
                 persona.live() — destiny entries due this minute → nudge
                 routine.trigger() — routines whose HH:MM matches now
```

---

## License

MIT
