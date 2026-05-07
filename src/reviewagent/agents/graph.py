from uuid import UUID

from reviewagent.agents.decision_agent import DecisionAgent
from reviewagent.agents.metadata_agent import MetadataAgent
from reviewagent.agents.state import ReviewState
from reviewagent.connectors.crossref import CrossrefConnector
from reviewagent.connectors.openalex import OpenAlexConnector
from reviewagent.llm.gateway import LLMGateway


class ReviewPipeline:
    """Sequential Phase 1 PoC pipeline: metadata -> decision."""

    def __init__(
        self,
        metadata_agent: MetadataAgent | None = None,
        decision_agent: DecisionAgent | None = None,
    ) -> None:
        self._metadata_agent = metadata_agent or MetadataAgent()
        self._decision_agent = decision_agent or DecisionAgent()

    async def run(self, submission_id: UUID, doi: str) -> ReviewState:
        state = ReviewState(submission_id=submission_id, doi=doi)

        meta_result = await self._metadata_agent.run(doi)
        state.errors.extend(meta_result.errors)

        if meta_result.cms is None:
            state.errors.append("No metadata could be fetched from any source")
            return state

        state.cms = meta_result.cms
        state.metadata_source = meta_result.source

        decision_result = await self._decision_agent.run(meta_result.cms, meta_result.errors)
        state.decision = decision_result.decision

        return state
