import json
import logging
import re
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)


def call_claude_mcp(prompt: str, timeout: int = 600) -> Optional[str]:
    """
    Run a prompt via the local `claude -p` CLI, which has access to PitchBook MCP tools.
    Requires Claude Code to be installed with PitchBook MCP configured.
    """
    try:
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            logger.warning("claude CLI exited %d: %s", result.returncode, result.stderr[:300])
            return None
        return result.stdout.strip()
    except FileNotFoundError:
        logger.error(
            "'claude' CLI not found. Install Claude Code: https://claude.ai/code"
        )
        return None
    except subprocess.TimeoutExpired:
        logger.error("claude CLI timed out after %ds", timeout)
        return None


def parse_json(text: str):
    """Extract a JSON value from Claude's response, handling code-fenced output."""
    if not text:
        return None
    if "```" in text:
        for block in text.split("```")[1::2]:
            cleaned = re.sub(r"^json\s*", "", block.strip())
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"(\[.*?\]|\{.*?\})", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    logger.warning("Could not parse JSON from claude output:\n%s", text[:400])
    return None
