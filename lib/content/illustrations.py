"""Illustrative (synthetic, not live) animated examples for the top of each
Learning lesson (README_forex.md Section 4.11).

Deliberately hand-built rather than real market data: real price action
doesn't reliably show a textbook-clean example of any given concept in a
random current window, and these exist purely to make one idea click
visually. Every rendering carries an explicit "illustrative, not real
market data" label — this must never be confused with the live examples
lower on each lesson page (those use real current data on purpose).

Built on Plotly's frame-based animation: each frame reveals one more
candle, plus optional shapes (zone/range rectangles) and an extra line
series (e.g. an EMA) that grows alongside it.
"""

import plotly.graph_objects as go

_UP_COLOR = "#26a69a"
_DOWN_COLOR = "#ef5350"


def build_animation(
    candles: list[dict],
    shapes_by_frame: list[list[dict]] | None = None,
    annotations_by_frame: list[list[dict]] | None = None,
    line_series: list[float] | None = None,
    line_name: str = "",
    y_range: tuple[float, float] | None = None,
    height: int = 320,
) -> go.Figure:
    """`candles`: list of {open, high, low, close} dicts, x-position implied
    by list order. `shapes_by_frame`/`annotations_by_frame`, if given, must
    have the same length as `candles` — index i is what's shown once candle
    i has been revealed. `line_series`, if given, is a same-length list of
    y-values (NaN before a point should appear) drawn as a second trace.
    """
    n = len(candles)
    xs = list(range(n))
    opens = [c["open"] for c in candles]
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    closes = [c["close"] for c in candles]

    def candle_trace(i: int) -> go.Candlestick:
        return go.Candlestick(
            x=xs[:i],
            open=opens[:i],
            high=highs[:i],
            low=lows[:i],
            close=closes[:i],
            increasing_line_color=_UP_COLOR,
            decreasing_line_color=_DOWN_COLOR,
            showlegend=False,
        )

    def line_trace(i: int) -> go.Scatter:
        ys = line_series[:i] if line_series else []
        return go.Scatter(
            x=xs[:i], y=ys, mode="lines", name=line_name,
            line=dict(color="#ffa726", width=2), showlegend=bool(line_name),
        )

    frames = []
    for i in range(1, n + 1):
        data = [candle_trace(i)]
        if line_series is not None:
            data.append(line_trace(i))
        frames.append(
            go.Frame(
                data=data,
                name=str(i),
                layout=go.Layout(
                    shapes=shapes_by_frame[i - 1] if shapes_by_frame else [],
                    annotations=annotations_by_frame[i - 1] if annotations_by_frame else [],
                ),
            )
        )

    initial_data = [candle_trace(1)]
    if line_series is not None:
        initial_data.append(line_trace(1))

    fig = go.Figure(data=initial_data, frames=frames)
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis=dict(range=[-0.5, n - 0.5], showticklabels=False, showgrid=False, zeroline=False),
        yaxis=dict(showgrid=False, showticklabels=False, range=y_range, zeroline=False),
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", y=1.1, x=0),
        updatemenus=[
            dict(
                type="buttons",
                showactive=False,
                y=1.22,
                x=0.0,
                xanchor="left",
                buttons=[
                    dict(
                        label="▶ Play",
                        method="animate",
                        args=[
                            None,
                            {
                                "frame": {"duration": 450, "redraw": True},
                                "fromcurrent": False,
                                "transition": {"duration": 0},
                            },
                        ],
                    ),
                    dict(
                        label="↺ Restart",
                        method="animate",
                        args=[
                            ["1"],
                            {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"},
                        ],
                    ),
                ],
            )
        ],
    )
    return fig


def _c(o: float, h: float, low: float, cl: float) -> dict:
    return {"open": o, "high": h, "low": low, "close": cl}


def market_structure_example() -> go.Figure:
    candles = [
        _c(100, 102, 99, 101),
        _c(101, 105, 100, 104),   # higher high
        _c(104, 104.5, 101.5, 102),
        _c(102, 102.5, 100.5, 101.5),  # higher low (above prior low ~99-100)
        _c(101.5, 108, 101, 107),  # higher high
        _c(107, 107.5, 104, 105),
        _c(105, 105.5, 103, 104.5),  # higher low
        _c(104.5, 111, 104, 110),  # higher high
    ]
    swing_low_idx, swing_low_y = 3, 100.5
    swing_high_idx, swing_high_y = 4, 108
    annotations = []
    for i in range(len(candles)):
        anns = []
        if i >= swing_low_idx:
            anns.append(dict(x=swing_low_idx, y=swing_low_y - 1.5, text="Higher Low", showarrow=False, font=dict(size=10, color="#26a69a")))
        if i >= swing_high_idx:
            anns.append(dict(x=swing_high_idx, y=swing_high_y + 1.5, text="Higher High", showarrow=False, font=dict(size=10, color="#26a69a")))
        annotations.append(anns)
    return build_animation(candles, annotations_by_frame=annotations, y_range=(97, 113))


def candlesticks_example() -> go.Figure:
    candles = [
        _c(100, 104, 99.5, 103.5),    # strong bullish, small wicks
        _c(103.5, 104, 99, 99.5),     # strong bearish
        _c(99.5, 103, 96, 99.6),      # long lower wick, rejection
        _c(99.6, 99.8, 99.4, 99.65),  # doji
    ]
    labels = [
        "Strong bullish (body dominates)",
        "Strong bearish (body dominates)",
        "Long lower wick (rejected lower prices)",
        "Doji (open ≈ close, indecision)",
    ]
    annotations_by_frame = [
        [
            dict(x=k, y=candles[k]["low"] - 1.8, text=labels[k], showarrow=False, font=dict(size=9))
            for k in range(i + 1)
        ]
        for i in range(len(candles))
    ]
    return build_animation(candles, annotations_by_frame=annotations_by_frame, y_range=(93, 106))


def support_resistance_example() -> go.Figure:
    support = 100.0
    candles = [
        _c(104, 105, 102, 102.5),
        _c(102.5, 103, 100.2, 100.5),  # touch 1
        _c(100.5, 103.5, 100.3, 103),  # bounce
        _c(103, 104, 102, 102.5),
        _c(102.5, 103, 100.1, 100.4),  # touch 2
        _c(100.4, 104, 100.2, 103.8),  # bounce
        _c(103.8, 104.5, 102.5, 103),
        _c(103, 103.2, 99, 99.2),      # breaks through
        _c(99.2, 100.3, 98.5, 100.1),  # retest as resistance
    ]
    shapes = []
    for i in range(len(candles)):
        line_shape = dict(
            type="line", x0=-0.5, x1=len(candles) - 0.5, y0=support, y1=support,
            line=dict(color="#ffa726", width=1.5, dash="dash"),
        )
        shapes.append([line_shape] if i >= 1 else [])
    annotations = []
    for i in range(len(candles)):
        anns = []
        if i >= 1:
            anns.append(dict(x=len(candles) - 1, y=support + 0.8, text="Support", showarrow=False, font=dict(size=10, color="#ffa726")))
        if i >= 7:
            anns.append(dict(x=8, y=support - 1.2, text="Breaks → flips to resistance", showarrow=False, font=dict(size=9, color="#ef5350")))
        annotations.append(anns)
    return build_animation(candles, shapes_by_frame=shapes, annotations_by_frame=annotations, y_range=(96, 107))


def risk_management_example() -> go.Figure:
    """Not a candle chart — an equity-curve comparison: 1% risk vs 8% risk
    across the same losing streak."""
    losses = [-1, -1, 1, -1, -1, -1, 2, -1, -1, 1]  # R-multiples of a rough losing streak
    conservative = [10000.0]
    aggressive = [10000.0]
    for r in losses:
        conservative.append(conservative[-1] * (1 + 0.01 * r))
        aggressive.append(aggressive[-1] * (1 + 0.08 * r))

    frames = []
    n = len(conservative)
    for i in range(1, n + 1):
        frames.append(
            go.Frame(
                data=[
                    go.Scatter(x=list(range(i)), y=conservative[:i], mode="lines", name="1% risk per trade", line=dict(color=_UP_COLOR, width=3)),
                    go.Scatter(x=list(range(i)), y=aggressive[:i], mode="lines", name="8% risk per trade", line=dict(color=_DOWN_COLOR, width=3)),
                ],
                name=str(i),
            )
        )
    fig = go.Figure(data=frames[0].data, frames=frames)
    fig.update_layout(
        height=320,
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis=dict(showticklabels=False, showgrid=False, title="Same losing streak, same 10 trades"),
        yaxis=dict(showgrid=False, title="Account value ($)"),
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=1.15, x=0),
        updatemenus=[
            dict(
                type="buttons", showactive=False, y=1.3, x=0.0, xanchor="left",
                buttons=[
                    dict(label="▶ Play", method="animate", args=[None, {"frame": {"duration": 450, "redraw": True}, "fromcurrent": False}]),
                    dict(label="↺ Restart", method="animate", args=[["1"], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}]),
                ],
            )
        ],
    )
    return fig


def fvg_supply_demand_example() -> go.Figure:
    candles = [
        _c(100, 101, 99.5, 100.3),
        _c(100.3, 100.8, 99.8, 100),
        _c(100, 100.5, 98.5, 98.8),   # the "last bearish candle" -> zone
        _c(98.8, 103, 98.7, 102.5),   # displacement candle 1
        _c(102.5, 106, 102.3, 105.5),  # displacement candle 2 (FVG forms vs candle before)
        _c(105.5, 108, 105, 107.5),   # displacement candle 3
        _c(107.5, 108, 105, 105.5),
        _c(105.5, 106, 100.5, 101),   # pullback into the zone
        _c(101, 105, 100.3, 104.5),   # bounce from zone
    ]
    zone_low, zone_high = 98.5, 98.8
    zone_start = 2
    fvg_low, fvg_high = candles[3]["high"], candles[5]["low"]  # gap between candle before push and candle after
    shapes = []
    annotations = []
    for i in range(len(candles)):
        s, a = [], []
        if i >= 3:
            s.append(dict(type="rect", x0=zone_start - 0.4, x1=len(candles) - 0.5, y0=zone_low, y1=zone_high,
                           fillcolor="rgba(38,166,154,0.25)", line=dict(width=0), layer="below"))
            a.append(dict(x=zone_start, y=zone_low - 1, text="Demand zone", showarrow=False, font=dict(size=10, color=_UP_COLOR)))
        if i >= 5:
            s.append(dict(type="rect", x0=3.5, x1=5.5, y0=fvg_low, y1=fvg_high,
                           fillcolor="rgba(255,167,38,0.3)", line=dict(width=0), layer="below"))
            a.append(dict(x=4.5, y=(fvg_low + fvg_high) / 2, text="FVG", showarrow=False, font=dict(size=10, color="#ffa726")))
        if i >= 8:
            a.append(dict(x=8, y=105.5, text="Price returns & bounces", showarrow=False, font=dict(size=9)))
        shapes.append(s)
        annotations.append(a)
    return build_animation(candles, shapes_by_frame=shapes, annotations_by_frame=annotations, y_range=(95, 111))


def trend_filters_example() -> go.Figure:
    candles = [
        _c(105, 105.5, 103, 103.5),
        _c(103.5, 104, 101.5, 102),
        _c(102, 103, 100.5, 101),
        _c(101, 102, 99.5, 100),
        _c(100, 103, 99.8, 102.5),   # crosses above EMA
        _c(102.5, 105, 102, 104.5),
        _c(104.5, 107, 104, 106.5),
        _c(106.5, 109, 106, 108.5),
    ]
    ema = [104, 103.2, 102.5, 101.8, 101.4, 101.3, 101.6, 102.2]
    annotations = []
    for i in range(len(candles)):
        a = []
        if i >= 4:
            a.append(dict(x=4, y=98.5, text="Price crosses above EMA", showarrow=False, font=dict(size=10, color=_UP_COLOR)))
        annotations.append(a)
    return build_animation(candles, annotations_by_frame=annotations, line_series=ema, line_name="200 EMA (illustrative)", y_range=(97, 111))


def orb_example() -> go.Figure:
    range_high, range_low = 101.5, 100.5
    candles = [
        _c(100.8, 101.5, 100.5, 101.2),  # the opening range candle
        _c(101.2, 101.4, 100.8, 101),
        _c(101, 101.3, 100.6, 100.9),
        _c(100.9, 104.5, 100.8, 104),    # aggressive breakout
        _c(104, 104.3, 102, 102.3),      # pullback to range edge
        _c(102.3, 105.5, 102, 105),      # continuation
    ]
    shapes = []
    annotations = []
    for i in range(len(candles)):
        s, a = [], []
        s.append(dict(type="rect", x0=-0.5, x1=len(candles) - 0.5, y0=range_low, y1=range_high,
                       fillcolor="rgba(255,167,38,0.15)", line=dict(color="#ffa726", width=1), layer="below"))
        a.append(dict(x=0, y=range_high + 0.6, text="09:30-09:45 opening range", showarrow=False, font=dict(size=9, color="#ffa726")))
        if i >= 3:
            a.append(dict(x=3, y=104.8, text="Aggressive breakout", showarrow=False, font=dict(size=10, color=_UP_COLOR)))
        if i >= 4:
            a.append(dict(x=4, y=101.6, text="Pullback to range edge = entry", showarrow=False, font=dict(size=9)))
        shapes.append(s)
        annotations.append(a)
    return build_animation(candles, shapes_by_frame=shapes, annotations_by_frame=annotations, y_range=(99, 107))


def signal_pipeline_example() -> go.Figure:
    """Reuses the FVG scenario (any qualifying setup would do) and adds a
    final "Signal generated" marker once every rule has been shown to pass."""
    candles = [
        _c(100, 101, 99.5, 100.3),
        _c(100.3, 100.8, 99.8, 100),
        _c(100, 100.5, 98.5, 98.8),
        _c(98.8, 103, 98.7, 102.5),
        _c(102.5, 106, 102.3, 105.5),
        _c(105.5, 108, 105, 107.5),
        _c(107.5, 108, 105, 105.5),
        _c(105.5, 106, 100.5, 101),
        _c(101, 105, 100.3, 104.5),
    ]
    zone_low, zone_high = 98.5, 98.8
    annotations = []
    for i in range(len(candles)):
        a = []
        if i >= 3:
            a.append(dict(x=2, y=zone_low - 1, text="Zone + FVG", showarrow=False, font=dict(size=9, color=_UP_COLOR)))
        if i >= 8:
            a.append(dict(x=8, y=106, text="✓ All rules passed — signal generated", showarrow=False,
                           font=dict(size=11, color="#26a69a", family="Arial Black")))
        annotations.append(a)
    return build_animation(candles, annotations_by_frame=annotations, y_range=(95, 111))
