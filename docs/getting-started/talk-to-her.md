# Talk to her

Three ways:

## Web UI

`http://localhost:5000` is the door. Type, send, read. Drag images to her if she has vision.

## Telegram / Discord

If you gave her a token in the wizard, you can also reach her there. Send the bot a message; she reads it on the next tick.

To verify the channel, message her `/start` from your account. She'll reply with a pairing code. Paste the code in the web UI's settings page; the channel becomes verified, and from then on she'll only listen to that account.

## OpenAI-compatible API

Her web server speaks OpenAI's Chat Completions API at `http://localhost:5000/v1`. From any tool that speaks OpenAI:

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:5000/v1", api_key="sk-no-need")

response = client.chat.completions.create(
    model="default",
    messages=[
        {"role": "user", "content": "What did we talk about yesterday?"}
    ],
)
print(response.choices[0].message.content)
```

The API key is ignored locally; pass anything. The `model` field is also ignored — she uses whatever model she's been configured with internally.

Use this to integrate her into your own workflows: a script that pings her on schedule, an editor plugin that asks her about your code, a tool that drops her into a longer pipeline.

## Continue to

[Read her files →](read-her-files.md) — see what she's learning about you on disk.
