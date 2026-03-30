"""CLI environment commands — check and prepare the runtime environment."""

import sys

from application.business import environment


async def dispatch(args):
    action = getattr(args, "action", None)

    if action == "check":
        outcome = await environment.check_model(args.model)
        if not outcome.success:
            print(f"Not ready: {outcome.message}")
            sys.exit(1)
        print(f"Model '{args.model}' is ready.")

    elif action == "prepare":
        outcome = await environment.prepare(args.model or None)
        if not outcome.success:
            print(f"Error: {outcome.message}")
            sys.exit(1)
        model = (outcome.data or {}).get("model", "")
        print(f"Environment is ready. Model: {model}")

    else:
        print("Usage: eternego env {check,prepare}")
        sys.exit(1)
