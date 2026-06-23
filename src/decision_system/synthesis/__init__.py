"""AI-assisted evidence synthesis package.

Provides prompt templates, structured output parsing, and the synthesis
service that ties provider calls, prompts, and parsing together.
"""

from decision_system.synthesis.prompts import (
    get_template,
    SynthesisMode,
    TEMPLATE_VERSION,
)

from decision_system.synthesis.parser import (
    parse_synthesis_output,
    DraftClaim,
    ParsedSynthesis,
)

from decision_system.synthesis.service import (
    run_synthesis,
    SynthesisResult,
    SYNTHESIS_MODES,
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
