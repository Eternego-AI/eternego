"""Web Search — how to search the web using DuckDuckGo."""

from application.core.brain.data import Skill


class WebSearch(Skill):
    name = "web-search"
    description = (
        "Provides commands for searching the web using DuckDuckGo's API "
        "without requiring an API key."
    )

    def __init__(self, persona):
        super().__init__(persona)

    def document(self):
        from application.core import paths
        workspace = str(paths.workspace(self.persona.id))
        return f"""# Web Search

Search using DuckDuckGo's instant answer API — no key required:

```json
{{"tool": "shell", "params": {{"command": "curl -s \\"https://api.duckduckgo.com/?q=YOUR+QUERY&format=json&no_redirect=1&no_html=1\\""}}}}
```

The `AbstractText` field contains a summary. `RelatedTopics` lists related results.

For broader web results:

```json
{{"tool": "shell", "params": {{"command": "curl -sA \\"Mozilla/5.0\\" \\"https://html.duckduckgo.com/html/?q=YOUR+QUERY\\""}}}}
```

## Save Before Processing

```json
{{"tool": "shell", "params": {{"command": "curl -s \\"https://api.duckduckgo.com/?q=YOUR+QUERY&format=json\\" > {workspace}/search.json"}}}}
```

Then parse with Python (see `python` skill) or jq:

```json
{{"tool": "shell", "params": {{"command": "jq '.RelatedTopics[].Text' {workspace}/search.json"}}}}
```

## Tips

- URL-encode spaces as `+` in the query string
- Add `site:example.com` to restrict to a domain
- After getting results, use `reflect` to seed the next tick with what you found — then `say` in the following tick with the actual data rather than guessing it at plan time"""
