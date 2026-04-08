"""CLI environment commands — check and prepare the runtime environment."""

import sys

from application.business import environment


async def dispatch(args):
    action = getattr(args, "action", None)

    if action == "check":
        from application.core.data import Model
        model = Model(
            name=args.model,
            provider=getattr(args, "provider", None),
            credentials={"api_key": getattr(args, "key", None)} if getattr(args, "key", None) else None,
        )
        outcome = await environment.check_model(model)
        if not outcome.success:
            print(f"Not ready: {outcome.message}")
            sys.exit(1)
        print(f"Model '{args.model}' is ready.")

    elif action == "prepare":
        outcome = await environment.prepare(
            model=args.model or None,
            provider=getattr(args, "provider", None),
            credentials=getattr(args, "key", None),
        )
        if not outcome.success:
            print(f"Error: {outcome.message}")
            sys.exit(1)
        model_obj = (outcome.data or {}).get("model")
        print(f"Environment is ready. Model: {model_obj.name if model_obj else ''}")

    else:
        print("Usage: eternego env {check,prepare}")
        sys.exit(1)
