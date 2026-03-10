"""Base agent class wrapping Google ADK Agent for EquityIQ analyst agents."""

from __future__ import annotations

import logging
from typing import Callable

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from config.analyst_personas import PERSONAS
from config.data_contracts import AnalystReport
from config.settings import get_settings

logger = logging.getLogger(__name__)

# Maps agent_name -> Settings attribute for the agent URL.
_AGENT_URL_MAP: dict[str, str] = {
    "valuation_scout": "VALUATION_AGENT_URL",
    "momentum_tracker": "MOMENTUM_AGENT_URL",
    "pulse_monitor": "PULSE_AGENT_URL",
    "economy_watcher": "ECONOMY_AGENT_URL",
    "compliance_checker": "COMPLIANCE_AGENT_URL",
    "signal_synthesizer": "SYNTHESIZER_AGENT_URL",
    "risk_guardian": "RISK_AGENT_URL",
}


class BaseAnalystAgent:
    """Base class for all EquityIQ analyst agents.

    Wraps a Google ADK ``Agent`` with EquityIQ conventions: persona from
    ``PERSONAS``, typed ``output_schema``, error-safe ``analyze()`` method,
    and A2A agent card generation.
    """

    def __init__(
        self,
        agent_name: str,
        output_schema: type[AnalystReport],
        tools: list[Callable] | None = None,
        model: str = "gemini-3-flash-preview",
    ) -> None:
        # Validate persona exists -- raises KeyError if missing.
        persona = PERSONAS[agent_name]

        self._name = agent_name
        self._persona = persona
        self._output_schema = output_schema
        self._tools = tools or []

        # Note: we intentionally omit output_schema from the ADK Agent to avoid
        # datetime serialization issues in ADK's _output_schema_processor.
        # Instead, we instruct the LLM to return JSON and parse it ourselves
        # in analyze() via model_validate_json().
        schema_json = output_schema.model_json_schema()
        self._agent = Agent(
            name=agent_name,
            model=model,
            instruction=(
                f"{persona}\n\n"
                "IMPORTANT: Return your analysis as a single JSON object matching this schema "
                f"(do NOT include 'timestamp'):\n{schema_json}"
            ),
            tools=self._tools,
        )

    # -- Properties -----------------------------------------------------------

    @property
    def agent(self) -> Agent:
        """Return the underlying ADK Agent instance."""
        return self._agent

    @property
    def name(self) -> str:
        """Agent name (key in PERSONAS dict)."""
        return self._name

    @property
    def persona(self) -> str:
        """System prompt from PERSONAS dict."""
        return self._persona

    # -- Core method ----------------------------------------------------------

    async def analyze(self, ticker: str) -> AnalystReport:
        """Run analysis for *ticker* and return a typed report.

        On any error returns a safe fallback: signal=HOLD, confidence=0.0.
        This method **never** raises.
        """
        try:
            session_service = InMemorySessionService()
            session = await session_service.create_session(
                app_name=self._name,
                user_id="equityiq",
            )

            runner = Runner(
                agent=self._agent,
                app_name=self._name,
                session_service=session_service,
            )

            user_content = types.Content(
                role="user",
                parts=[types.Part(text=f"Analyze stock ticker: {ticker}")],
            )

            final_text: str | None = None
            async for event in runner.run_async(
                user_id="equityiq",
                session_id=session.id,
                new_message=user_content,
            ):
                if event.is_final_response() and event.content and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            final_text = part.text
                            break

            if final_text is None:
                return self._fallback_report(ticker, "No response received from LLM")

            # Strip markdown code fences if the LLM wraps the JSON.
            cleaned = final_text.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[-1]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3].strip()

            return self._output_schema.model_validate_json(cleaned)

        except Exception as exc:
            logger.warning("Agent %s failed for %s: %s", self._name, ticker, exc)
            return self._fallback_report(ticker, str(exc))

    # -- Agent card -----------------------------------------------------------

    def get_agent_card(self) -> dict:
        """Generate an A2A-compatible agent card for discovery."""
        settings = get_settings()
        url_attr = _AGENT_URL_MAP.get(self._name, "")
        url = getattr(settings, url_attr, "http://localhost:8000") if url_attr else ""

        # First sentence of persona as description.
        description = self._persona.split(".")[0].strip() + "." if self._persona else ""

        return {
            "name": self._name,
            "description": description,
            "url": url,
            "capabilities": [fn.__name__ for fn in self._tools],
            "output_schema": self._output_schema.__name__,
        }

    # -- Helpers --------------------------------------------------------------

    def _fallback_report(self, ticker: str, error_message: str) -> AnalystReport:
        """Return a safe HOLD/0.0 report on failure."""
        return AnalystReport(
            ticker=ticker,
            agent_name=self._name,
            signal="HOLD",
            confidence=0.0,
            reasoning=f"Analysis failed: {error_message}",
        )


def create_agent(
    agent_name: str,
    output_schema: type[AnalystReport],
    tools: list[Callable] | None = None,
    model: str = "gemini-3-flash-preview",
) -> BaseAnalystAgent:
    """Convenience factory that returns a ``BaseAnalystAgent`` instance."""
    return BaseAnalystAgent(
        agent_name=agent_name,
        output_schema=output_schema,
        tools=tools,
        model=model,
    )
