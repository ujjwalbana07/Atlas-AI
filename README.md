# Atlas AI

Atlas AI is a reviewable travel-planning workspace. Describe the trip you want, let a group of specialist agents assemble the research, then edit or approve the draft before the final itinerary is written.

The interface is designed to feel like a travel studio rather than a chat box: it helps turn a rough idea into a practical route with flights, accommodation, weather, budget guidance, and day-by-day plans.

## What It Does

- **Supervisor routing** chooses the useful specialists for each request.
- **Travel guardrails** keep unrelated or unsafe requests out of the planning workflow.
- **Global airport lookup** searches the bundled worldwide catalog of more than 7,800 IATA airports using city names, airport names, IATA codes, and ICAO codes. There is no country whitelist or single-country restriction.
- **Flight research** uses AviationStack MCP when the service is configured and supplements it with the global airport catalog.
- **Hotel research** uses Tavily MCP.
- **Weather research** uses the local weather MCP server and OpenWeather.
- **Budget analysis** highlights cost categories, risks, and ways to save.
- **Human-in-the-loop review** pauses after the draft itinerary is created.
- **Feedback-driven revisions** regenerate the itinerary before producing the final answer. Explicit changes such as “make this 5-day trip 10 days” are treated as required changes.
- **Export tools** let you copy the result or download it as a PDF from the browser.

## How The Workflow Works

```mermaid
flowchart LR
		A[Travel request] --> B[Guardrail]
		B --> C[Supervisor]
		C --> D[Specialist agents]
		D --> E[Draft itinerary]
		E --> F{Human review}
		F -->|Approve| G[Final travel plan]
		F -->|Request changes| H[Revise itinerary]
		H --> G
```

The draft is stored in a PostgreSQL-backed LangGraph checkpoint. The approval request and its thread ID can therefore be resumed through the browser or API.

## Project Structure

| Path | Purpose |
| --- | --- |
| `app.py` | FastAPI application, browser route, API endpoints, and health check |
| `backend.py` | LangGraph state, supervisor, specialist agents, global airport lookup, HITL routing, and final response generation |
| `mcp_client.py` | MCP client configuration for Tavily, AviationStack, and weather tools |
| `custom_weather_mcp_server.py` | Local MCP server exposing current weather and forecast tools |
| `templates/index.html` | Travel studio page and HITL controls |
| `static/style.css` | Base layout styles |
| `static/travel-theme.css` | Travel-focused visual theme |
| `requirements.txt` | Python dependencies |

## Requirements

- Python 3.10 or newer
- PostgreSQL database with a reachable connection string
- A Groq API key
- `uv`/`uvx` for the AviationStack MCP adapter
- Optional live-service keys for Tavily, AviationStack, and OpenWeather

The airport catalog itself is bundled through `airportsdata`, so global airport lookup does not depend on a live AviationStack response.

## Local Setup

### macOS and Linux

```bash
git clone https://github.com/ujjwalbana07/Atlas-AI.git
cd Atlas-AI

python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### Windows PowerShell

```powershell
git clone https://github.com/ujjwalbana07/Atlas-AI.git
cd Atlas-AI

py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Create a `.env` file in the project root:

```dotenv
DATABASE_URL=postgresql://user:password@host:5432/database
GROQ_API_KEY=your_groq_key
GROQ_MODEL=openai/gpt-oss-120b

# Required for the related live MCP services.
TAVILY_API_KEY=your_tavily_key
AVIATION_STACK_API_KEY=your_aviationstack_key
OPENWEATHER_API_KEY=your_openweather_key

# Optional default origin when a request does not specify one.
DEFAULT_ORIGIN_CITY=Dallas, Texas
DEFAULT_ORIGIN_IATA=DFW
```

Start the development server:

```bash
uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 in a browser.

The app can also be started with:

```bash
python app.py
```

## API

### Create a draft

```bash
curl -X POST http://127.0.0.1:8000/api/travel \
	-H "Content-Type: application/json" \
	-d '{"message":"Plan a 10-day Japan trip with flights, hotels, weather and a mid-range budget."}'
```

The response includes a `thread_id`, the draft itinerary, selected agents, and `requires_approval: true` when the graph is paused for review.

### Approve a draft

```bash
curl -X POST http://127.0.0.1:8000/api/travel/approve \
	-H "Content-Type: application/json" \
	-d '{"thread_id":"user_<id>","approved":true,"feedback":""}'
```

### Request a revision

```bash
curl -X POST http://127.0.0.1:8000/api/travel/approve \
	-H "Content-Type: application/json" \
	-d '{"thread_id":"user_<id>","approved":false,"feedback":"Change the trip from 5 days to 10 days and add the extra days."}'
```

### Health check

```bash
curl http://127.0.0.1:8000/health
```

## Global Airport Coverage

Global lookup is backed by `airportsdata.load("IATA")`. The application loads the complete catalog and does not filter airports by country. A request can reference:

- Any city or country supported by the catalog
- IATA codes such as `LHR`, `DEL`, or `HND`
- ICAO codes such as `EGLL`, `VIDP`, or `RJTT`
- Airport names such as Heathrow, Indira Gandhi, or Haneda

When a request names an airport or city, matching records are passed into the flight agent with their IATA code, ICAO code, airport name, city, and country. When no specific airport is named, the agent receives the full-catalog count and is instructed to reason globally rather than assume one country.

## Troubleshooting

- **Python version errors:** use Python 3.10 or newer. Some current LangGraph pins do not install on Python 3.9.
- **Missing `DATABASE_URL` or `GROQ_API_KEY`:** add the values to `.env` before importing the backend.
- **AviationStack or weather errors:** the relevant live service key or MCP adapter may be unavailable. The workflow catches those failures and labels live data as unavailable instead of blocking the entire plan.
- **`uvx` not found:** install `uv`, then verify it with `uvx --version`.
- **Approval does not resume:** use the same `thread_id` returned by `POST /api/travel` when calling the approval endpoint.

## Development

The FastAPI routes are asynchronous, while the existing LangGraph convenience functions are synchronous. `nest_asyncio` is applied in `app.py` so the MCP helpers can be called from the current workflow.

Before opening a pull request, run:

```bash
python -m py_compile app.py backend.py mcp_client.py custom_weather_mcp_server.py
```

Then exercise a normal draft, an approval, and a revision through the browser or API.

## License

See [LICENSE](LICENSE).
