"""Shareable content — text, PDF, and branded PNG cards — for social posts.

Started as the Bot page's report (README_forex.md Section 11) and later
extended to Strategy Lab, Backtesting, and Scanner (Section 11, "more social
lead" pass) so the same anti-hype-compliant share pattern doesn't have to be
re-invented per page.

Anti-hype discipline (README_forex.md Section 7) applies *more* here, not
less: this content is designed to leave the app and be read with zero
context by strangers on social media. Every version — text, PDF, or image —
always carries the sample size and a "preliminary until ~30 trades" flag
when under that floor, and never states or implies a win rate is proof of
edge. Nothing here may claim a guarantee, and there is no code path that
omits the disclaimer to make a post "cleaner."

Image cards use Pillow only — no matplotlib/kaleido. Pillow is already a
transitive dependency of both `fpdf2` and `streamlit` (pinned directly here
since we now import it ourselves), and `ImageFont.load_default(size=...)`
uses Pillow's own bundled font rather than a system font path — the same
"don't depend on something that only happens to exist on this machine"
lesson as the `zoneinfo`/`tzdata` and PDF-font issues already hit twice
this project (Section 11).
"""

from datetime import datetime
from io import BytesIO
from urllib.parse import quote

import streamlit as st
from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont

BASE_URL = "https://tradelab.streamlit.app"
APP_URL = f"{BASE_URL}/Bot"
RELIABLE_SAMPLE_FLOOR = 30

SETUP_LABELS = {
    "trend_aligned_pullback": "Trend-Aligned Pullback",
    "supply_demand_fvg": "Supply & Demand + FVG",
    "opening_range_breakout": "Opening Range Breakout",
}

# --- Card image styling (shared by every build_*_image function) ------------
_CARD_W, _CARD_H = 1200, 630
_NAVY = (20, 40, 60)
_GRAY = (100, 100, 100)
_LIGHT_GRAY = (160, 160, 160)
_ACCENT = (230, 235, 240)
_WARN = (150, 60, 0)
_WHITE = (255, 255, 255)


def _font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.load_default(size=size)


def _safe_text(text: str) -> str:
    """Pillow's bundled `load_default()` font — deliberately used instead of
    a system font path, see module docstring — doesn't cover em/en-dashes or
    smart quotes, rendering them as a tofu box. Same class of bug as the
    fpdf2/Helvetica Latin-1 issue (README_forex.md Section 11): sanitize at
    the render boundary rather than trust every caller to avoid the glyph."""
    return (
        text.replace("—", "-")
        .replace("–", "-")
        .replace("’", "'")
        .replace("‘", "'")
        .replace("“", '"')
        .replace("”", '"')
        .replace("…", "...")
    )


def _new_card() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (_CARD_W, _CARD_H), _WHITE)
    return img, ImageDraw.Draw(img)


def _draw_header(draw: ImageDraw.ImageDraw, subtitle: str) -> int:
    draw.text((40, 36), "TradeLab", font=_font(40), fill=_NAVY)
    draw.text((40, 84), _safe_text(subtitle), font=_font(20), fill=_GRAY)
    draw.line((40, 118, _CARD_W - 40, 118), fill=_ACCENT, width=2)
    return 140


def _draw_footer(draw: ImageDraw.ImageDraw, sample_size: int, reliable: bool) -> None:
    if not reliable:
        draw.text(
            (40, _CARD_H - 90),
            f"Preliminary - under the {RELIABLE_SAMPLE_FLOOR}-trade reliability floor ({sample_size} so far).",
            font=_font(16),
            fill=_WARN,
        )
    draw.text(
        (40, _CARD_H - 62),
        "Not financial advice - a rules-based research & education tool, not a signal-selling service.",
        font=_font(15),
        fill=_GRAY,
    )
    draw.text(
        (40, _CARD_H - 34),
        f"{BASE_URL} - generated {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}",
        font=_font(14),
        fill=_LIGHT_GRAY,
    )


def _to_png_bytes(img: Image.Image) -> bytes:
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


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


def build_stat_card_image(
    title: str,
    subtitle: str,
    stats: list[tuple[str, str]],
    *,
    sample_size: int = RELIABLE_SAMPLE_FLOOR,
    reliable: bool = True,
) -> bytes:
    """Generic branded stat card — a title, up to ~5 label/value pairs, and
    the standard disclaimer footer. Used wherever there's no time series to
    plot (a single signal, a scan summary) — see `build_equity_curve_image`
    for the backtest-with-a-curve case."""
    img, draw = _new_card()
    y = _draw_header(draw, subtitle)

    draw.text((40, y), _safe_text(title), font=_font(28), fill=_NAVY)
    y += 56

    col_w = (_CARD_W - 80) // 2
    for i, (label, value) in enumerate(stats[:6]):
        cx = 40 + (i % 2) * col_w
        cy = y + (i // 2) * 90
        draw.text((cx, cy), _safe_text(label), font=_font(17), fill=_GRAY)
        draw.text((cx, cy + 26), _safe_text(value), font=_font(32), fill=_NAVY)

    _draw_footer(draw, sample_size, reliable)
    return _to_png_bytes(img)


def build_equity_curve_image(
    asset: str,
    setup_label: str,
    report,  # StrategyPerformanceReport — typed loosely to avoid a schemas import cycle
) -> bytes:
    """Branded PNG of a backtest's cumulative-R equity curve, plotted with
    Pillow directly (no matplotlib/kaleido — see module docstring)."""
    img, draw = _new_card()
    y = _draw_header(draw, f"{asset} — {setup_label} — {report.sample_size} trades")

    curve = report.equity_curve
    chart_top, chart_bottom = y + 10, _CARD_H - 190
    chart_left, chart_right = 40, _CARD_W - 40

    if len(curve) >= 2:
        values = [0.0, *curve]
        lo, hi = min(values), max(values)
        span = (hi - lo) or 1.0
        zero_y = chart_bottom - ((0.0 - lo) / span) * (chart_bottom - chart_top)
        draw.line((chart_left, zero_y, chart_right, zero_y), fill=_ACCENT, width=2)

        n = len(values)
        step_x = (chart_right - chart_left) / (n - 1)
        points = [
            (chart_left + i * step_x, chart_bottom - ((v - lo) / span) * (chart_bottom - chart_top))
            for i, v in enumerate(values)
        ]
        line_color = (20, 130, 70) if curve[-1] >= 0 else (170, 40, 40)
        draw.line(points, fill=line_color, width=4, joint="curve")
    else:
        draw.text((chart_left, (chart_top + chart_bottom) // 2), "Not enough closed trades yet for a curve.", font=_font(18), fill=_GRAY)

    stats = [
        ("Win rate", f"{report.win_rate:.0%}"),
        ("Profit factor", f"{report.profit_factor:.2f}" if report.profit_factor != float("inf") else "Inf"),
        ("Expectancy (R)", f"{report.expectancy:+.2f}"),
        ("Max drawdown (R)", f"{report.max_drawdown:.2f}"),
    ]
    col_w = (_CARD_W - 80) // 4
    for i, (label, value) in enumerate(stats):
        cx = 40 + i * col_w
        draw.text((cx, chart_bottom + 16), _safe_text(label), font=_font(15), fill=_GRAY)
        draw.text((cx, chart_bottom + 38), _safe_text(value), font=_font(24), fill=_NAVY)

    _draw_footer(draw, report.sample_size, report.sample_size >= RELIABLE_SAMPLE_FLOOR)
    return _to_png_bytes(img)


def build_signal_share_text(asset: str, setup_label: str, signal) -> str:  # signal: TradingSignal
    lines = [
        f"🧪 TradeLab Strategy Lab — {asset}",
        f"{signal.direction} setup found: {setup_label}",
        f"Entry zone {signal.entry_zone[0]:g}–{signal.entry_zone[1]:g} · Stop {signal.stop_loss:g} · R:R {signal.risk_reward_ratio:.2f}",
        "",
        "Rules-based signal, not a prediction — full reasoning is on the page. Not financial advice.",
        f"See it live: {BASE_URL}/Strategy_Lab",
    ]
    return "\n".join(lines)


def build_backtest_share_text(asset: str, setup_label: str, report) -> str:  # report: StrategyPerformanceReport
    reliable = report.sample_size >= RELIABLE_SAMPLE_FLOOR
    reliability_note = "" if reliable else f" (preliminary — under the {RELIABLE_SAMPLE_FLOOR}-trade floor)"
    lines = [
        f"📉 TradeLab Backtest — {asset} — {setup_label}",
        f"{report.sample_size} trades, {report.date_range[0]} to {report.date_range[1]}",
        f"Win rate {report.win_rate:.0%} · Expectancy {report.expectancy:+.2f}R · Max drawdown {report.max_drawdown:.2f}R{reliability_note}",
        "",
        "Historical backtest only — not evidence of future performance, not financial advice.",
        f"See it live: {BASE_URL}/Backtesting",
    ]
    return "\n".join(lines)


def build_scanner_share_text(tier_counts: dict[str, int], top_picks: list[dict]) -> str:
    lines = [
        "🔎 TradeLab Market Scanner",
        f"🟢 {tier_counts.get('HIGH_QUALITY_SETUPS', 0)} High-Quality · "
        f"🟡 {tier_counts.get('WATCHLIST', 0)} Watchlist · "
        f"⚪ {tier_counts.get('WEAK_SETUPS', 0)} Weak · "
        f"🔴 {tier_counts.get('NO_TRADE', 0)} No Trade",
    ]
    if top_picks:
        lines.append("")
        lines.append("Top of the High-Quality tier right now:")
        for p in top_picks[:5]:
            lines.append(f"- {p['asset']}: {p['direction']} (confidence {p['confidence']:.0%})")
    lines.append("")
    lines.append("Rules-based ranking, not a prediction — an empty High-Quality tier is a normal result. Not financial advice.")
    lines.append(f"See it live: {BASE_URL}/Scanner")
    return "\n".join(lines)


def render_share_section(
    text: str,
    *,
    pdf_bytes: bytes | None = None,
    pdf_filename: str = "tradelab-report.pdf",
    image_bytes: bytes | None = None,
    image_filename: str = "tradelab-share.png",
    url: str = APP_URL,
) -> None:
    """Shared Share-section UI: text block, optional PDF/image downloads, and
    social share-intent links — used by every page that shares content, so
    the anti-hype caption and link set can't drift between pages."""
    st.caption(
        "Every format includes the disclaimer and sample size up front — this leaves the app and "
        "gets read with zero context, so the anti-hype rules apply here more than anywhere else, not less."
    )
    sc1, sc2 = st.columns([3, 2])
    with sc1:
        st.code(text, language=None)
        if image_bytes:
            st.image(image_bytes)
    with sc2:
        if pdf_bytes:
            st.download_button(
                "⬇️ Download PDF report", data=pdf_bytes, file_name=pdf_filename, mime="application/pdf", width="stretch"
            )
        if image_bytes:
            st.download_button(
                "🖼️ Download image", data=image_bytes, file_name=image_filename, mime="image/png", width="stretch"
            )
        encoded_text = quote(text)
        encoded_url = quote(url)
        st.link_button("Share on X", f"https://twitter.com/intent/tweet?text={encoded_text}", width="stretch")
        st.link_button("Share on LinkedIn", f"https://www.linkedin.com/sharing/share-offsite/?url={encoded_url}", width="stretch")
        st.link_button("Share on WhatsApp", f"https://wa.me/?text={encoded_text}", width="stretch")
        st.link_button("Share on Telegram", f"https://t.me/share/url?url={encoded_url}&text={encoded_text}", width="stretch")


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
