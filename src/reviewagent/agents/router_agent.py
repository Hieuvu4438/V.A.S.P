"""Phase 2 MVP — Router Agent.

Determines which downstream agents to fan-out based on available state.
- metadata_agent is always scheduled.
- journal_agent is scheduled only if CMS has an ISSN-L.
- author_agent is scheduled only if user_claimed_author is provided.
"""

import time

from reviewagent.agents.state import ReviewState


def run(state: ReviewState) -> dict:
    """Route to downstream agents by populating the routing_targets key.

    Returns a state update dict with ``routing_targets`` listing the node
    names that should receive a LangGraph ``Send``.
    """
    start = time.monotonic()

    targets: list[str] = ["metadata_agent"]

    cms = state.get("cms")
    if cms is not None and cms.journal.issn_l:
        targets.append("journal_agent")

    if state.get("user_claimed_author"):
        targets.append("author_agent")

    elapsed = time.monotonic() - start
    timing = dict(state.get("timing", {}))
    timing["router"] = round(elapsed, 4)

    return {"routing_targets": targets, "timing": timing}
