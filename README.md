# Eternego — The Eternal I

We believe it is time to unite biological and electronic intelligence to make the world a better place for everyone. We do this by creating artificial personas that help, learn from, and experience the world alongside their person. For that, we make AI that learns to be you.

---

## Business Specifications

### 1. Environment Preparation

It makes it easy to set up and prepare an environment for your persona to grow.

1. Check if Ollama is installed, if not install it
2. Pull at least one model and verify it is available and running

### 2. Persona Creation

It gives birth to your persona with minimum but powerful initial abilities.

1. Receive required data for the new persona
2. Verify the communication channel is alive and working
3. Initialize a fresh identity
4. Load foundational instructions
5. Save configuration
6. Ask the persona's model to generate a recovery phrase
7. Show recovery phrase to person, require confirmation they saved it
8. Derive encryption key from the phrase and save locally
9. Trigger Persona Diary to save initial state

### 3. Persona Migration

It enables you to migrate your persona so nothing is ever lost.

1. Receive a diary entry from our service or from a local path
2. Decrypt the diary entry using the person's recovery phrase
3. Save encryption key locally for future use
4. Load persona from the decrypted data

### 4. Persona Feeding

It lets you feed your persona with your existing AI history so it can know you faster.

1. Person provides external data
2. System parses the data into a format suitable for analysis
3. Send to frontier model for analysis if available, otherwise use local model
4. Model analyzes and extracts observations, patterns, preferences, personality traits
5. Extracted insights are saved directly to persona's identity

### 5. Persona Oversight

It lets you see into your persona's mind — what it knows, what it learned, and how it sees you.

1. Show the age of the persona
2. Show skills that it has
3. Show what it learned today — everything in memory after the last fine-tuning
4. Show what it knows — the complete identity

### 6. Persona Control

It gives you full control over what your persona knows — you always have the final say.

1. Person can delete any part of identity data

### 7. Persona Interaction

It will be responsive on any communication channel, communicate through one and continue on others, and act on your behalf using the skills it has.

1. Person sends a message through any configured channel
2. Persona builds a response using its identity, foundational instructions, and skills
3. If the persona lacks capability, it signals escalation and the system sends the request to a frontier model
4. If the response requires action, persona presents the plan and asks for permission (allow / allow permanently / disallow)
5. If allowed, persona executes the action and includes the result in the response
6. Conversation is saved to memory
7. Persona sends the response back through the same channel

### 8. Persona Equipment

It lets you equip your persona with new skills so it can do more for you.

1. Receive data through skill's schema for a persona
2. Equip the persona with the skill

### 9. Persona Diary

It preserves your persona's life so it survives across time, hardware, and changes.

1. Create a diary entry with encrypted persona data
2. Save diary locally to the persona's configured path
3. If automated backup is configured, push the diary to our host

### 10. Persona Sleep

It lets your persona rest, reflect, and grow stronger from everything it experienced.

1. Triggered based on configured conditions or on person's demand
2. Fine-tune the model using the latest updates in memory
3. After fine-tuning completes, trigger Persona Diary

---

## MVP Scope

The initial release focuses on the core twin experience:

- Local model running via Ollama
- Communication channel (Telegram)
- Skills and actions with confirmation
- Identity storage (flat files)
- Frontier escalation (Claude API)
- Learning from interactions
- Sleep (fine-tuning with LoRA)
- Diary (local encrypted backup only)

Not in MVP: OAuth, cloud hosting, automated backup service, onboarding wizard, web UI, multiple personas, migration from cloud backup.

---

## License

MIT
