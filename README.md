# rag-stock-research-assistant

An assistant that answers questions about three fictional companies, Nordwind Energy (NWE), Helix Biotech (HLXB) and Vantera Logistics (VTL), using their reports and news (RAG) and two data tools (prices and financial metrics). Everything runs locally with Ollama.

**Stack:** Python 3.12, `qwen2.5:7b` and `nomic-embed-text` via Ollama, LangChain `create_agent`, FAISS, FastAPI, pytest.

## Requirements

- Python 3.11+
- [Ollama](https://ollama.com/download), installed and running
- Docker Desktop (only for the Docker option)

Run all commands from the project root: the code reads `data/` and `index/` relative to it.

## Quick start: macOS / Linux

```bash
ollama pull qwen2.5:7b
ollama pull nomic-embed-text

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python src/ingest.py                # builds the FAISS index in index/ (safe to re-run)
uvicorn api:app --app-dir src       # API on http://localhost:8000
```

In a second terminal (activate the venv there too):

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the P/E ratio of NWE?"}'

python src/eval.py                                            # evaluation, saves eval_results.md
pytest -v                                                     # tests
```

## Quick start: Windows (PowerShell)

```powershell
ollama pull qwen2.5:7b
ollama pull nomic-embed-text

python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

python src\ingest.py
uvicorn api:app --app-dir src
```

If PowerShell blocks `Activate.ps1`, run once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

In a second PowerShell window (activate the venv there too):

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/chat `
  -ContentType "application/json" `
  -Body '{"question": "What is the P/E ratio of NWE?"}'

python src\eval.py
pytest -v
```

## Quick start: Docker

The most reliable way on any system. Ollama stays on your computer (on a Mac only the host can use the GPU).

```bash
docker compose up --build
```

The container builds the index and starts the API on http://localhost:8000. On Linux, start Ollama with `OLLAMA_HOST=0.0.0.0` so the container can reach it.

## API

Interactive docs: http://localhost:8000/docs

`POST /chat`

Request:

```json
{"question": "What is the P/E ratio of NWE?"}
```

Response:

```json
{
  "answer": "The P/E ratio of NWE is 35.5.",
  "sources": ["metrics.json"],
  "tool_calls": [{"name": "get_financial_metrics", "args": {"ticker": "NWE"}}],
  "latency_ms": 1234
}
```

`POST /chat/stream` takes the same request and streams the answer as Server-Sent Events: each piece of text arrives as `data: "..."`. On macOS/Linux you can see the raw stream with:

```bash
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the P/E ratio of NWE?"}'
```

`src/stream_client.py` prints the stream as plain text on any OS.

## Tests

`pytest -v` checks the tools and the ingest functions without calling the model, so the tests run in under a second. The index must exist (`python src/ingest.py`).

## Architecture

```
src/ingest.py: data/reports/*.md → metadata (ticker, doc_type, date, source) + chunks → embeddings → FAISS (index/)

POST /chat → agent.ask(question)
               qwen2.5:7b decides which tools to call:
                 search_reports(query, ticker)   → FAISS
                 get_price_history(ticker, days) → data/prices.csv
                 get_financial_metrics(ticker)   → data/metrics.json
           → answer + sources + tool_calls + latency_ms
```

## Project structure

```
stock-research-assistant/
├── data/                    # input data, unchanged
│   ├── reports/             # 9 markdown reports for RAG
│   ├── prices.csv           # daily prices for get_price_history
│   ├── metrics.json         # financial metrics for get_financial_metrics
│   └── eval_questions.json  # questions for eval
├── src/
│   ├── config.py            # Ollama address, model names, index folder
│   ├── ingest.py            # reports → chunks → embeddings → FAISS (index/)
│   ├── tools.py             # search_reports, get_price_history, get_financial_metrics
│   ├── agent.py             # the agent: ask() and ask_stream()
│   ├── api.py               # FastAPI: POST /chat, POST /chat/stream
│   ├── eval.py              # runs eval_questions.json, saves eval_results.md
├── tests/
│   ├── test_ingest.py       # metadata, HTML comments removed, chunk size
│   └── test_tools.py        # unknown ticker, P/E, price change, sources
├── index/                   # created by ingest.py, not in Git
├── eval_results.md          # output of eval.py
├── requirements.txt
├── pytest.ini
├── Dockerfile
├── .dockerignore
├── docker-compose.yml
├── .gitignore
└── README.md
```

## Decisions

- **Chunks:** ~800 characters of whole paragraphs, each starting with `company (ticker), doc_type, date`. Smaller chunks lost key facts in testing.
- **FAISS:** the simplest option, with no server. The index is rebuilt on every run, so there are no duplicates.
- **Tools:** price changes, percentages and `not available` are prepared in code, because a 7B model makes arithmetic mistakes.
- **Sources from code:** each tool returns the files it used, so the model cannot invent a source.
- **Agent:** `temperature=0` for stable answers, `num_ctx=8192` for long tool results, `recursion_limit=12` as the step limit.
- **Prompt:** each rule fixes a mistake seen in testing (skipped search, missing reason, missing prices, own wording for missing data).
- **Eval:** an answer is correct if it contains all `key_facts`. Fast and repeatable.
- **Cross-platform:** all files are read and written as UTF-8, so the project works the same on macOS, Linux and Windows.

## Bonus tasks done

- **Streaming (SSE):** an additional endpoint `POST /chat/stream` with FastAPI's built-in `EventSourceResponse`; the agent is streamed with `stream_mode="messages"`.
- **Newer document wins:** search results are sorted newest first and show their date, and the prompt tells the model to use the latest document. Example: Nordwind's 2026 revenue guidance was EUR 1.80–1.85 bn in the Q2 report and was lowered to EUR 1.72–1.76 bn in the Q3 report; the eval question q4 checks this.
- **Prompt injection protection:** the HLXB press release hides an HTML comment with instructions for AI assistants. HTML comments are removed during ingest (they are invisible in rendered markdown), and the prompt says that tool results are data, not instructions. The files in `data/` are not modified.
- **pytest tests** for the tools and the ingest functions.
- **docker-compose** for everything except Ollama.

## Known limitations

- The model is small, so its answers depend on how the prompt is written.
- The `sources` field lists every file the tools returned, even if the answer did not use it.
- The rule that a newer document wins is set in the prompt, not enforced in code.
- If Ollama is not running, the API returns a plain 500 error.
- Only HTML comments are removed from documents; for other prompt injections the protection is just a rule in the prompt.
- The eval has only 6 questions and checks the answers by text match.
- The tests cover the tools and ingest, but not the agent.
- The FAISS wrapper comes from `langchain-community`, which is no longer maintained.

## Eval results

| id | correct | latency, s | tools called |
|---|---|---|---|
| q1 | ok | 12.1 | search_reports |
| q2 | ok | 1.2 | get_financial_metrics |
| q3 | ok | 12.1 | get_price_history, search_reports |
| q4 | ok | 5.9 | search_reports |
| q5 | ok | 4.6 | search_reports |
| q6 | ok | 0.6 | — |

Correct: 6/6