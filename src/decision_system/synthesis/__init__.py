"""AI-assisted evidence synthesis package.

Provides prompt templates, structured output parsing, and the synthesis
service that ties provider calls, prompts, and parsing together.
"""

from decision_system.synthesis.parser import (
    DraftClaim,
    ParsedSynthesis,
    parse_synthesis_output,
)
from decision_system.synthesis.prompts import (
    TEMPLATE_VERSION,
    SynthesisMode,
    get_template,
)
from decision_system.synthesis.service import (
    SYNTHESIS_MODES,
    SynthesisResult,
    run_synthesis,
)

__all__ = [
    "get_template",
    "SynthesisMode",
    "TEMPLATE_VERSION",
    "parse_synthesis_output",
    "DraftClaim",
    "ParsedSynthesis",
    "run_synthesis",
    "SynthesisResult",
    "SYNTHESIS_MODES",
]
