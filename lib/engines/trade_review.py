"""Trade Review AI (README_forex.md Section 4.8), via Google Gemini's free tier.

Reviews PROCESS, not outcome — a losing trade that followed the plan is a
good process; a winning trade that ignored the stated risk rules is a bad
one that got lucky. The prompt is built to keep that distinction explicit
rather than let the model anchor on win/loss.

Scope note: this reviews what's actually recorded on the JournalEntry
(reason for entry/exit, stated risk, mistakes, emotional state) — it does
not have a live-linked TradingSignal/Strategy object to compare against,
since strategy persistence (Section 4.5) isn't built yet. That's a real
limitation, not hidden: the review prompt says so, and so should any UI
that renders it.
"""

from lib.schemas import JournalEntry
from lib.secrets import get_secret

_MODEL = "gemini-3.6-flash"

_SYSTEM_PROMPT = """You are a trading process coach, not a P&L commentator. \
Your job is to assess whether the trader followed a sound process — not whether the trade won or lost.

Rules:
- Never praise a trade just because it won, or criticize one just because it lost.
- Call out any mismatch between the stated entry reason and what actually happened.
- If risk:reward or position sizing looks unsound given the numbers provided, say so plainly.
- If the trader logged a mistake or an emotional state, address it directly rather than glossing over it.
- Keep it to 3-5 concise, specific sentences. No generic trading platitudes.
- You are not given the original strategy/signal object — only what the trader logged. Do not \
  claim knowledge of anything beyond what's given below."""


def is_configured() -> bool:
    return bool(get_secret("GEMINI_API_KEY"))


def _build_prompt(entry: JournalEntry) -> str:
    risk = abs(entry.entry - entry.stop_loss)
    reward = abs(entry.take_profit - entry.entry)
    rr = reward / risk if risk > 0 else 0.0

    lines = [
        f"Asset: {entry.asset}, Direction: {entry.direction}, Timeframe: {entry.timeframe}",
        f"Entry: {entry.entry}, Stop: {entry.stop_loss}, Target: {entry.take_profit} (planned R:R {rr:.2f})",
        f"Position size: {entry.position_size}, Risk amount: ${entry.risk_amount}",
        f"Reason for entry: {entry.reason_for_entry}",
        f"Result: {entry.result}" + (f", R multiple: {entry.r_multiple}" if entry.r_multiple is not None else ""),
    ]
    if entry.reason_for_exit:
        lines.append(f"Reason for exit: {entry.reason_for_exit}")
    if entry.mistakes:
        lines.append(f"Self-reported mistakes: {', '.join(entry.mistakes)}")
    if entry.emotional_state:
        lines.append(f"Emotional state: {entry.emotional_state}")
    if entry.lessons_learned:
        lines.append(f"Lessons learned (self-reported): {entry.lessons_learned}")

    return "\n".join(lines)


def review_trade(entry: JournalEntry) -> str:
    if not is_configured():
        raise RuntimeError("GEMINI_API_KEY is not set — see .streamlit/secrets.toml.example")
    if entry.result not in ("WIN", "LOSS", "BREAKEVEN"):
        raise ValueError("Can only review a closed trade (result must be WIN/LOSS/BREAKEVEN)")

    from google import genai  # imported lazily so the module loads even without the package present

    client = genai.Client(api_key=get_secret("GEMINI_API_KEY"))
    response = client.models.generate_content(
        model=_MODEL,
        contents=_build_prompt(entry),
        config={"system_instruction": _SYSTEM_PROMPT},
    )
    return response.text
