# Web Search

Search using DuckDuckGo's instant answer API — no key required:

```
curl -s "https://api.duckduckgo.com/?q=YOUR+QUERY&format=json&no_redirect=1&no_html=1"
```

The `AbstractText` field contains a summary. `RelatedTopics` lists related results.

For broader web results, use the HTML endpoint and extract links:

```
curl -sA "Mozilla/5.0" "https://html.duckduckgo.com/html/?q=YOUR+QUERY"
```

## Save Before Processing

```
curl -s "https://api.duckduckgo.com/?q=YOUR+QUERY&format=json" > {workspace}/search.json
```

Parse with `python` (see `python` skill) or `jq` if available:

```
jq '.RelatedTopics[].Text' {workspace}/search.json
```

## Tips

- URL-encode spaces as `+` in the query string
- Add `site:example.com` to restrict to a domain
- Summarise findings with `say` rather than dumping raw results to the person
