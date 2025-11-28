# MCP-Aligned Self-Hosted Financial Agent

This document outlines how to host the AI financial assistant using the Model Context Protocol (MCP) pattern. The goal is privacy-first deployment where data, tools, and the conversational agent all run on your own infrastructure.

## Layer 1: Data Layer (The Source)
* **Role:** Secure storage and aggregation of transactions, accounts, budgets, goals, and categorization feedback vectors.
* **Stack:** PostgreSQL with `pgvector` for embeddings; optional Redpanda or NATS JetStream for ingest buffering. Encrypt backups with Litestream or WAL-G.

## Layer 2: MCP Server Layer (The Tools/Logic)
* **Role:** Expose finance operations as MCP tools and enforce auth/logging.
* **Stack:** Python 3.11+, FastAPI, SQLAlchemy, Pandas/NumPy, statsmodels/Prophet (time-series), scikit-learn (categorization), Pydantic schemas, served via uvicorn.
* **Core tool functions:**
  - `predict_cash_balance(period_days)`: forecast net cash with income, recurring bills, and discretionary spend.
  - `calculate_debt_avalanche(debts)`: compute payoff ordering and schedule by APR (avalanche method).
  - `get_anomaly_flags(category, last_30_days)`: flag spikes/duplicates and overspend pacing risks.
  - `calc_required_savings(goal_amount, goal_date)`: required recurring contributions to hit a goal safely.
  - `categorize_transaction(description)`: predict category using a lightweight model + pgvector similarity and learn from corrections.

## Layer 3: AI Agent Layer (The Conversation)
* **Role:** Runs the chat loop, selects/executes MCP tools, and streams responses to the user.
* **Stack:** Self-hosted LLM runtime (LM Studio or Ollama with Mixtral/Llama 3), orchestration with LangGraph or LlamaIndex, and a private web UI (Open WebUI or Text-Generation-WebUI).

## Integration Notes
* The current Streamlit app surfaces insights but does **not** yet include the MCP server or on-device LLM runtime; use this guide to stand up those layers alongside the app.
* Keep API keys and model artifacts outside the repo; mount them as secrets or volumes in deployment.
* Log tool calls/audit events in the database to trace how insights were generated.
