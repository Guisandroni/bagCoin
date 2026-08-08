"""LangGraph node handlers for the BagCoin orchestrator, organized by domain.

Each module exports node functions `(AgentState) -> AgentState` that the
orchestrator graph registers. The orchestrator re-exports them for
backwards compatibility with callers that import from
`app.agents.orchestrator`.
"""
