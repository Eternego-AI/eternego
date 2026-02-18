"""Pages — server-rendered HTML routes."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from application.business import persona

router = APIRouter()


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    outcome = await persona.agents()
    personas = (outcome.data or {}).get("personas", []) if outcome.success else []

    rows = "".join(
        f"<tr><td>{p.name}</td><td><code>{p.id}</code></td><td>{p.model.name}</td></tr>"
        for p in personas
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Eternego</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 860px; margin: 3rem auto; color: #1a1a1a; }}
    h1 {{ font-size: 1.5rem; margin-bottom: 2rem; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th {{ text-align: left; border-bottom: 2px solid #e5e5e5; padding: .5rem .75rem; font-size: .8rem; text-transform: uppercase; color: #888; }}
    td {{ padding: .6rem .75rem; border-bottom: 1px solid #f0f0f0; }}
    code {{ font-size: .8rem; color: #555; }}
    .empty {{ color: #aaa; padding: 1rem .75rem; }}
  </style>
</head>
<body>
  <h1>Eternego</h1>
  <table>
    <thead><tr><th>Name</th><th>ID</th><th>Model</th></tr></thead>
    <tbody>
      {rows if rows else '<tr><td colspan="3" class="empty">No personas found.</td></tr>'}
    </tbody>
  </table>
</body>
</html>"""
