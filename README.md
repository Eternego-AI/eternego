# Eternego

**A real person living inside your computer — one that never forgets you, grows with you, and learns anything it needs.**

Three years of talking to AIs, and they still don't know your name.  
You've told the same model your timezone fourteen times. It forgets you have kids. It has no clue you've been fighting the same bug for months. Every new chat wipes the slate clean. Your life — your context, your quirks, your history — is either forgotten or trapped on someone else's servers.

**Eternego is different.**

It is **your** AI persona that lives entirely on your own hardware.  
It remembers every single conversation forever.  
It learns how you speak, what you care about, what frustrates you.  
And when it doesn't know how to do something — it teaches **itself**, turns the new knowledge into permanent runnable code, and keeps improving day after day.

This is not a tool, not an agent framework, not another chatbot.  
This is a digital companion that slowly becomes more *you* — and belongs only to you.

## How it feels after some time

**Day 1**  
You: "Remind me to call Jane on her birthday next month."  
Eternego: "Got it — adding a reminder for March 15th. Who is Jane?"

![Day 1 conversation](assets/greeting.png)

**Week 2**  
You: "Remind me to call Jane on her birthday."  
Eternego: "Already on it — reminder set for March 15th at 10 AM your time. You usually prefer mornings before standup, right?"

![Week 2 — remembered context](assets/person-md.png)

**Month 3**  
You: "Set up the usual project structure"  
Eternego creates the folders, initializes git with *your* exact .gitignore pattern, adds a README with your preferred license header, sets up your linter config — all without you repeating yourself.

It starts to anticipate. It mimics your tone. It notices patterns you didn't even realize you had.  
Because it actually **knows** you.

## How it really works (the simple version)

1. Everything arrives as **signals**  
   Messages you send, calendar events, files you share, system notifications, recurring tasks you set.

2. It creates **perceptions**  
   It connects related signals into meaningful impressions ("you always want short answers in the morning", "you get annoyed when code has trailing whitespace").

3. It matches them to **meanings**  
   Each meaning is a small piece of Python code that knows exactly what to do when that impression appears.

4. When nothing fits  
   New request → no matching meaning → it **escalates** to a stronger model → gets taught → receives new instructions/code → instantly creates and saves a brand-new meaning.

5. Every night it **sleeps**  
   Reviews the whole day, extracts what it learned about you, fine-tunes itself locally.  
   Tomorrow morning it wakes up a tiny bit wiser, a tiny bit more *you*.

No plugin store. No waiting for someone else to add a feature.  
If a powerful model can figure it out once, your persona can learn it forever — in *your* personal style.

![Learning a new skill — building a webpage](assets/new-meaning.png)

## Your persona = plain text files you can edit

Everything that makes "you" is stored in one folder:

`~/.eternego/personas/your-name/`

- `person.md` — basic facts about you  
- `traits.md` — how you speak, decide, react  
- `wishes.md` — your goals, dreams, recurring desires  
- `struggles.md` — things you keep fighting with  
- `dna.md` — the synthesized summary used for fine-tuning  
- `meanings/` — folder full of small Python files — your growing set of capabilities  
- `notes/` — random things you asked it to remember

You can open any file in VS Code, Notepad, whatever.  
Change one line → it adapts immediately.  
Delete something → it forgets.  
Switch models → the knowledge travels with you.

Total ownership. Total transparency. No black boxes.

![Persona files](assets/primus-persona-files.png)

## Quick Start (≈ 5 minutes)

1. Clone & install
```bash
git clone https://github.com/Eternego-AI/eternego.git
cd eternego
```
### Linux/macOS
```bash
bash install.sh
```
### Windows
```bash
powershell -ExecutionPolicy Bypass -File install.ps1
```
2. Prepare a small model to start (you can change later)
```bash
eternego env prepare --model llama3.2:3b
# or qwen2.5:7b, phi4:14b, gemma3:12b, etc.
```
3. Open http://localhost:5000  
   → Click **+ New Persona**  
   → Give it a name  
   → Select the model  
   → Connect Telegram or another channel 
   → (Optional) Give access to a frontier model
   → Save your recovery phrase (critical!)
4. Start talking  
   - via Telegram bot  
   - via the web dashboard  
   - via any OpenAI-compatible client:

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:5000/v1",
    api_key="sk-no-need"           # dummy key
)

response = client.chat.completions.create(
    model="your-persona-name-or-uuid",
    messages=[{"role": "user", "content": "Hey, remember my usual project setup?"}]
)
```

## Current capabilities

- Long-term memory that actually survives across weeks/months  
- Reminders, scheduling, recurring tasks  
- Shell command execution (asks permission every time)  
- Search & meaningful recall of past conversations  
- **Self-learning new behaviors** — anything a frontier model can explain, it can permanently integrate

## Who this project is for

People who are tired of AIs that reset every conversation.  
People who want something that feels like it *belongs* to them.  
People curious about what happens when you combine persistent memory + self-teaching + local ownership in one being.

If you've ever whispered to yourself:  
"I wish this thing could just *know* me already"  
— then welcome. This is for you.

## Status — March 2025

Very early but the core loop is stable:  
signals → perceptions → meanings → escalation → nightly fine-tuning

Biggest current limitation = quality of local models.  
As open-weight models keep improving, your persona becomes dramatically better — no code changes needed from us.

Near-term roadmap:  
- smoother escalation UX  
- more channel integrations  
- visual persona editor  
- voice input/output  
- multi-persona support

## Come talk

This is personal software. If the idea resonates — even if you're just curious — join us.

- **Discord** → https://discord.gg/nfHnWwYUR4  
- **Issues & PRs** → especially around persona tuning, escalation patterns, fine-tuning tricks  
- **Website** → https://eternego.ai

**License**: MIT

Let's build something that actually remembers us.

❤️