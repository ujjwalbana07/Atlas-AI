# Atlas AI

Travel planner built with FastAPI, LangGraph, Groq, Tavily, and AviationStack.

## Run with Docker

1. Start Docker Desktop.
2. Copy `.env.example` to `.env` if you do not already have one, and fill in your API keys and PostgreSQL connection URL.
3. Build and run:

```sh
docker build -t atlas-ai .
docker run -d --name atlas-ai --env-file .env -p 8000:8000 atlas-ai
```

Open http://localhost:8000. Check the running app with:

```sh
docker ps
curl http://localhost:8000/health
docker logs atlas-ai
```

The health endpoint checks the web server; it does not verify external services.
The travel planner requires a reachable PostgreSQL database and valid API keys.
Secrets in `.env` are excluded from Git and the Docker build context.
