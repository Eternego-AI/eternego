# Eternego — The Eternal I

We believe it is time to unite biological and electronic intelligence to make the world a better place for everyone. We do this by creating artificial personas that help, learn from, and experience the world alongside their person. For that, we make AI that learns to be you.

---

## Business Specifications

### 1. Environment Preparation

It makes it easy to set up and prepare an environment for your persona to grow.

1. Check if required tools are installed, if not install them
2. Check if a local inference engine is installed, if not install it
3. Pull at least one model and verify it is available and running

### 2. Persona Creation

It gives birth to your persona with minimum but powerful initial abilities.

1. Receive required data for the new persona
2. Verify the communication channel is alive and working
3. Initialize a fresh identity
4. Copy the base model into a persona-owned model
5. Build the agent's storage and create its DNA
6. Start the persona's history
7. Load foundational instructions and equip basic skills
8. Bond the person to the persona
9. If a frontier model is provided, enable escalation
10. Save configuration
11. Ask the persona's model to generate a recovery phrase
11. Save encryption key to secure storage
12. Open and write the initial diary entry

### 3. Persona Migration

It enables you to migrate your persona so nothing is ever lost.

1. Receive a diary entry from a local path and the recovery phrase
2. Verify the environment is ready
3. Decrypt and restore the persona from the diary
4. Copy the base model into a persona-owned model
5. Save configuration
6. Extract observations from DNA to populate traits and context
7. Save encryption key to secure storage
8. Open and write a new diary entry on the new host
9. Verify all communication channels and report status

### 4. Persona Feeding

It lets you feed your persona with your existing AI history so it can know you faster.

1. Person provides external data and its source
2. System parses the data into a common format
3. Model analyzes and extracts observations
4. Extracted insights are saved to persona's identity through growth

### 5. Persona Oversight

It lets you look into your persona's mind — what it knows, what it learned, and how it sees you.

1. Load all persona knowledge: person facts, person traits, agent identity, agent context, skills, and conversations
2. Assign trackable IDs to each entry for precise control
3. Return everything organized by category

### 6. Persona Control

It gives you full control over what your persona knows — you always have the final say.

1. Receive one or more trackable entry IDs
2. Identify the source of each entry from its prefix
3. Remove the entry from the corresponding storage
4. Report what was removed

### 7. Persona Interaction

It gives the persona the ability to sense, think, communicate, act, escalate, and reflect — like a mind.

The interaction system follows a cognitive architecture. There are two loops: a reactive loop where the persona senses and responds, and a proactive loop where the persona anticipates and acts on its own.

#### 7a. Sense

It lets the persona sense a stimulus from a channel and process it.

1. Receive a message and channel from the person
2. Give the stimulus to the agent
3. The agent thinks, yielding thoughts one by one
4. Each thought is routed by its intent:
   - Saying → communicate through the channel
   - Doing → execute the action
   - Consulting → escalate to a frontier model
   - Reasoning → internal process, shared as context only
5. After all thoughts are processed, reflect

#### 7b. Say

It lets the persona express a thought through a channel.

1. Order all relevant channels to communicate the thought
2. When a channel confirms delivery, record that the person heard it
3. If no channel delivered, report failure

#### 7c. Act

It lets the persona act on the world by executing a tool call.

1. Ask the person for permission to execute the tool call
2. If authorized, execute the tool call on the person's system
3. Note the result so the agent can continue

#### 7d. Escalate

It lets the persona escalate to a frontier model when the task exceeds its ability.

1. Send the prompt to the frontier model
2. The frontier thinks using the same thought pattern
3. For each frontier thought, route through say and act
4. After completion, give the agent the full observation to learn from

The agent does not observe the frontier's reasoning process. It should develop its own reasoning for similar situations, not imitate the frontier's thought process.

#### 7e. Reflect

It lets the persona reflect on what it learned from the interaction.

1. Give the agent a reflection prompt
2. The agent thinks, yielding thoughts
3. Route saying and reasoning thoughts

#### 7f. Predict

It lets the persona anticipate and act without external stimulus.

1. Give the agent a prediction prompt
2. The agent thinks, yielding thoughts
3. Route saying and reasoning thoughts

### 8. Persona Equipment

It lets you equip your persona with new skills so it can do more for you.

1. Receive a skill document for a persona
2. Equip the persona with the skill

### 9. Persona Diary

It preserves your persona's life so it survives across time, hardware, and changes.

1. Retrieve the encryption phrase from secure storage
2. Create an encrypted diary entry with all persona data
3. Save diary locally with version control

### 10. Persona Sleep

It lets your persona rest, reflect, and grow stronger from everything it experienced.

1. Check if there are observations newer than the current model
2. Extract observations and grow the persona
3. Synthesize new DNA from previous DNA, current traits, and context
4. Generate training data from DNA
5. Fine-tune the model
6. Verify the fine-tuned model responds correctly
7. Delete the old persona model
8. Save the new model to persona configuration
9. Trigger Persona Diary

### 11. List Personas

It returns all personas in the system.

1. Load all personas from the agents home directory (each subdirectory that has a config file)
2. Return an outcome with the list of personas in the payload

### 12. Find Persona by Channel

It finds the persona that owns a given communication channel.

1. Get all personas (via list personas)
2. For each persona, check if any of its channels matches the given channel (same name and credentials)
3. Return the first matching persona in the outcome payload, or failure if none matches

### 13. Persona Start

It opens all channels for a persona and starts listening for messages.

1. Verify the persona has channels configured
2. For each channel, start listening and route incoming messages to sense
3. In group chats, only respond when the persona is mentioned

### 14. Persona Stop

It closes all channels for a persona.

1. Close all active channel connections for the persona
2. Report what was stopped

---

## License

MIT
