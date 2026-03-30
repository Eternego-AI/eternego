"""CLI pair command — pair a channel using a code sent by the persona."""

import json
import sys
import urllib.error
import urllib.request

from config import web as web_config


def run(args):
    service_url = f"http://{web_config.HOST}:{web_config.PORT}"
    try:
        urllib.request.urlopen(
            urllib.request.Request(
                f"{service_url}/api/pair/{args.code}",
                method="POST",
            )
        )
        print("Channel paired successfully.")
    except urllib.error.HTTPError as e:
        body = json.loads(e.read())
        print(f"Error: {body.get('detail', 'Unknown error')}")
        sys.exit(1)
    except urllib.error.URLError:
        print(f"Error: Could not connect to the Eternego service at {service_url}. Is it running?")
        sys.exit(1)
