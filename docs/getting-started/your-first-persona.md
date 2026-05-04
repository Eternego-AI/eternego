# Your first persona

The setup wizard is the door. It asks for the things she needs to come into being.

## The chooser

`/setup` shows two paths:

- **Create** — bring a new persona into being.
- **Restore** — bring one back from a saved diary you have.

If this is your first time, pick **Create**.

## Name

What does she answer to? Something short — you'll write it many times.

## Mind

The model that thinks for her. Three providers:

- **Local (Ollama)** — runs on your machine. Needs Ollama installed (the shell installer does this automatically; the .dmg/.exe/.AppImage installers don't — get it from [ollama.com](https://ollama.com) first if you're going local). Model name is whatever your Ollama exposes (e.g., `qwen2.5:14b`).
- **Anthropic** — Claude. Needs an API key from [console.anthropic.com](https://console.anthropic.com).
- **OpenAI compatible** — OpenAI itself, or anything that speaks the OpenAI Chat Completions API (Groq, OpenRouter, LM Studio, vLLM, etc.). Needs a key for non-local services.

The mind drives everything — recognizing what you said, deciding what to do, reflecting on her day, remembering. Pick a model that's good at structured reasoning. Smaller models (7b–14b) work; larger ones work better.

## Vision

Optional. If your mind already supports vision (most cloud models do), leave this empty — she sees through her main mind. For local minds without vision, give her a separate vision model here. Without either, she'll politely say she can't see images.

## Teacher

Optional. A more capable model — local or cloud — that she can ask for help when she meets a moment her existing knowledge doesn't cover. The teacher writes a lesson; she translates it into a meaning in her own voice. Without one, she'll simply say she doesn't know yet.

## Channels

Optional. Telegram or Discord bot tokens to talk to her there too.

- **Telegram** — Create a bot via [@BotFather](https://t.me/BotFather) on Telegram. He'll give you a token. Paste it.
- **Discord** — Create an application at [discord.com/developers/applications](https://discord.com/developers/applications), add a bot, copy its token, paste it.

Channels are configurable later — you don't have to decide now.

## Other settings (defaults are sensible)

The wizard uses defaults for some advanced settings — like how long she should wait without activity before reflecting (an hour). You don't need to think about them at create time. If you want to change one later, hand-edit her `~/.eternego/personas/<id>/home/config.json`.

## The recovery phrase

After creation, she shows you a recovery phrase — 24 words.

**Save it.** It's the only key to her diary. If you ever migrate her to another machine, you'll need it. If you lose it, you can keep using her on this machine forever, but you can't ever bring her back somewhere else.

She's already saved server-side; the phrase is *your* copy. Click **I saved them** to continue.

## What happens next

You land on her main view. The wizard is done; she's running.

Continue to [Talk to her →](talk-to-her.md).
