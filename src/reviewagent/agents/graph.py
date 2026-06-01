"""Phase 2 MVP — LangGraph parallel orchestration.

Converts the sequential Phase 1 pipeline into a LangGraph StateGraph
with parallel fan-out via the Send API.

Structure:
  START -> router
  router -> (metadata_agent | journal_agent | author_agent)  [parallel via Send]
  all three -> aggregator  [barrier]
  aggregator -> decision_agent -> END
"""

import logging
from typing import Any

from langgraph.constants import END, START, Send
from langgraph.graph import StateGraph

from reviewagent.agents import (
    aggregator_agent,
    author_agent,
    decision_agent,
    journal_agent,
    metadata_agent,
    router_agent,
)
from reviewagent.agents.state import ReviewState

logger = logging.getLogger(__name__)


def _route_from_router(state: ReviewState) -> list[Send]:
    """Fan-out from router to the agents listed in routing_targets."""
    targets = state.get("routing_targets", ["metadata_agent"])
    sends: list[Send] = []
    for target in targets:
        sends.append(Send(target, state))
    return sends


def build_graph() -> StateGraph:
    """Build and compile the Phase 2 LangGraph pipeline."""
    builder = StateGraph(ReviewState)

    # Nodes
    builder.add_node("router", router_agent.run)
    builder.add_node("metadata_agent", metadata_agent.run)
    builder.add_node("journal_agent", journal_agent.run)
    builder.add_node("author_agent", author_agent.run)
    builder.add_node("aggregator", aggregator_agent.run)
    builder.add_node("decision_agent", decision_agent.run)

    # Edges
    builder.add_edge(START, "router")

    # Fan-out: router decides which agents to invoke in parallel
    builder.add_conditional_edges("router", _route_from_router)

    # All agents feed into the aggregator (barrier)
    builder.add_edge("metadata_agent", "aggregator")
    builder.add_edge("journal_agent", "aggregator")
    builder.add_edge("author_agent", "aggregator")

    # Aggregator -> Decision -> END
    builder.add_edge("aggregator", "decision_agent")
    builder.add_edge("decision_agent", END)

    return builder.compile()


class ReviewPipeline:
    """Phase 2 pipeline wrapper that invokes the LangGraph graph."""

    def __init__(self) -> None:
        self._graph = build_graph()

    async def run(
        self,
        submission_id: str,
        doi: str,
        user_claimed_author: str | None = None,
        user_claimed_affiliation: str | None = None,
    ) -> ReviewState:
        """Execute the full review pipeline."""
        initial_state: ReviewState = {
            "submission_id": submission_id,
            "doi": doi,
            "user_claimed_author": user_claimed_author,
            "user_claimed_affiliation": user_claimed_affiliation,
            "cms": None,
            "journal_result": None,
            "author_result": None,
            "decision": None,
            "errors": [],
            "metadata_source": None,
            "prompt_version": "decision_v2",
            "timing": {},
        }

        result = await self._graph.ainvoke(initial_state)
        return result  # type: ignore[return-value]
