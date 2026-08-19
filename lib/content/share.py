"""Shareable Bot report — text (for social posts) and PDF (README_forex.md
Section 11's paper trading bot).

Anti-hype discipline (README_forex.md Section 7) applies *more* here, not
less: this content is designed to leave the app and be read with zero
context by strangers on social media. Every version — text or PDF — always
carries the sample size and a "preliminary until ~30 trades" flag when
under that floor, and never states or implies a win rate is proof of edge.
Nothing here may claim a guarantee, and there is no code path that omits
the disclaimer to make a post "cleaner."
"""

from datetime import datetime

from fpdf import FPDF

APP_URL = "https://tradelab.streamlit.app/Bot"
RELIABLE_SAMPLE_FLOOR = 30

SETUP_LABELS = {
    "trend_aligned_pullback": "Trend-Aligned Pullback",
    "supply_demand_fvg": "Supply & Demand + FVG",
    "opening_range_breakout": "Opening Range Breakout",
}


def _track_record(closed_trades: list[dict]) -> tuple[int, float, float, bool]:
    n = len(closed_trades)
    if n == 0:
        return 0, 0.0, 0.0, False
    wins = [t for t in closed_trades if float(t["r_multiple"] or 0) > 0]
    win_rate = len(wins) / n
    total_r = sum(float(t["r_multiple"] or 0) for t in closed_trades)
    return n, win_rate, total_r, n >= RELIABLE_SAMPLE_FLOOR


def build_share_text(open_trades: list[dict], closed_trades: list[dict]) -> str:
    n, win_rate, total_r, reliable = _track_record(closed_trades)
    lines = ["🤖 TradeLab Paper Trading Bot"]

    if n == 0:
        lines.append("No closed trades yet — the bot is still building its track record.")
    else:
        reliability_note = "" if reliable else f" (preliminary — under the {RELIABLE_SAMPLE_FLOOR}-trade floor)"
        lines.append(f"Track record: {n} closed trades, {win_rate:.0%} win rate, {total_r:+.2f} total R{reliability_note}.")

    lines.append(f"{len(open_trades)} trade(s) currently open/pending across 3 rules-based setups.")
    lines.append("")
    lines.append("Not financial advice — a rules-based research & education tool. Every trade's full reasoning is on the page.")
    lines.append(f"See it live: {APP_URL}")
    return "\n".join(lines)


class _TradeLabPDF(FPDF):
    def header(self) -> None:
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(20, 40, 60)
        self.cell(0, 10, "TradeLab", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 6, "Paper Trading Bot Report", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(200, 200, 200)
        self.line(10, self.get_y() + 2, 200, self.get_y() + 2)
        self.ln(8)

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"tradelab.streamlit.app - generated {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}", align="C")


def build_share_pdf(open_trades: list[dict], closed_trades: list[dict]) -> bytes:
    pdf = _TradeLabPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    n, win_rate, total_r, reliable = _track_record(closed_trades)

    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(20, 40, 60)
    pdf.cell(0, 8, "Disclaimer", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(60, 60, 60)
    pdf.multi_cell(
        0,
        5,
        "Not financial advice, not a signal-selling service. TradeLab is a rules-based research and "
        "education tool - every trade below fired because it met a predefined, published rule set, "
        "shown with its full reasoning. Past results, especially on small samples, are not evidence "
        "of future performance.",
    )
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(20, 40, 60)
    pdf.cell(0, 8, "Track Record", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(0, 0, 0)
    if n == 0:
        pdf.cell(0, 6, "No closed trades yet.", new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.cell(0, 6, f"Closed trades: {n}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 6, f"Win rate: {win_rate:.0%}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 6, f"Total R: {total_r:+.2f}", new_x="LMARGIN", new_y="NEXT")
        if not reliable:
            pdf.set_font("Helvetica", "I", 9)
            pdf.set_text_color(150, 60, 0)
            pdf.multi_cell(
                0, 5,
                f"Preliminary: below the {RELIABLE_SAMPLE_FLOOR}-trade floor TradeLab requires before "
                "treating a win rate as a reliable estimate of edge.",
            )
    pdf.ln(4)

    def trades_table(title: str, trades: list[dict]) -> None:
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(20, 40, 60)
        pdf.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        if not trades:
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 6, "None.", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
            return

        pdf.set_font("Helvetica", "B", 8)
        pdf.set_fill_color(230, 235, 240)
        pdf.set_text_color(0, 0, 0)
        headers = ["Asset", "Setup", "Dir", "Status", "R:R", "Result"]
        widths = [25, 55, 15, 25, 20, 30]
        for h, w in zip(headers, widths):
            pdf.cell(w, 7, h, border=1, fill=True)
        pdf.ln()

        pdf.set_font("Helvetica", "", 8)
        for t in trades:
            result = ""
            if t.get("status") == "CLOSED":
                r = float(t["r_multiple"] or 0)
                result = f"{t['exit_reason']} ({r:+.2f}R)"
            row = [
                t["asset"],
                SETUP_LABELS.get(t["setup_type"], t["setup_type"]),
                t["direction"],
                t["status"],
                f"{float(t['risk_reward_ratio']):.2f}",
                result,
            ]
            for val, w in zip(row, widths):
                pdf.cell(w, 6, str(val), border=1)
            pdf.ln()
        pdf.ln(4)

    trades_table("Open & Pending", open_trades)
    trades_table("Recently Closed", closed_trades[:15])

    output = pdf.output()
    return bytes(output)
