# Deploying Zena (Shiny for Python)

The course requires a **working public URL**. Below are practical paths; pick one your team can maintain through the term.

## Prerequisites

- `requirements.txt` installs successfully on the host.
- **Ollama:** For full AI text, use **Ollama Cloud** (`OLLAMA_API_KEY` in `.env`) on hosted environments where local Ollama is not available. The app falls back to non-LLM text if Ollama fails.
- **RAG database:** `data/zena_rag.db` is created automatically on first run when `init_rag_db()` runs from `app.py`. Ensure the process can write under `data/`.
- **Optional password:** Set `ZENA_APP_PASSWORD` in the host environment so only your class can access the deployment; put the password in your Canvas .docx.

## Option A — shinyapps.io (Posit)

1. Create an account at [shinyapps.io](https://www.shinyapps.io).  
2. Install `rsconnect` (R) or use the **Posit** publishing flow for **Shiny for Python** as documented in [Shiny for Python deployment](https://shiny.posit.co/py/docs/deploy.html).  
3. Set environment variables in the shinyapps.io dashboard (**Settings → Variables**) for `OLLAMA_API_KEY`, `ZENA_APP_PASSWORD`, etc.  
4. Publish `app.py` as the application entrypoint. Include `data/` seed if you pre-bundle the SQLite file, or allow first-run creation.

## Option B — Posit Connect

1. Your institution may provide Connect — request a **Python Shiny** asset.  
2. Use `manifest.json` / `requirements.txt` per Connect docs; set env vars in the Connect UI.  
3. Entry command typically mirrors: `shiny run app.py` or the Connect equivalent.

## Option C — Docker / VPS (e.g. DigitalOcean)

1. Base image: `python:3.12-slim`.  
2. `COPY` the project, `pip install -r requirements.txt`.  
3. Expose a port; run `shiny run app.py --host 0.0.0.0 --port 8080` (or use `uvicorn` only if you expose a different stack — for Zena, use Shiny’s server).  
4. Put TLS in front with Caddy or nginx.

## Smoke test before submitting

- [ ] Open the public URL in an incognito window.  
- [ ] Complete one full flow: Generate → see charts + agent panels + plan text.  
- [ ] If password-protected, confirm wrong password fails and correct password works.  
- [ ] Paste the **exact URL** into your .docx (no localhost).

## Troubleshooting

| Symptom | Likely cause |
|---------|----------------|
| Blank AI text | Missing `OLLAMA_API_KEY` on host or network block to Ollama |
| 500 on first load | Cannot write `data/zena_rag.db` — fix filesystem permissions |
| Sidebar stuck on Access | Wrong `ZENA_APP_PASSWORD` or env not set on server |
