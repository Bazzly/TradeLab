"""Static, zero-API Economic Calendar (README_forex.md Section 4.10).

No external API. After FMP and Finnhub both turned out to be paid-only for
this specific endpoint (despite requiring a key on their free tier too —
verified live against real keys, 2026-08-19) and BLS blocks automated
fetches of its own release-schedule pages (403), this covers only the
handful of recurring events that move markets most, sourced directly from
official calendars:

- FOMC rate decisions: federalreserve.gov/monetarypolicy/fomccalendars.htm,
  fetched 2026-08-19. The SECOND day of each two-day meeting is listed —
  that's when the statement + press conference happen.
- ECB Governing Council monetary policy meetings: ecb.europa.eu/press/
  calendars/mgcgc, fetched 2026-08-19 (that page only lists meetings from
  the fetch date forward, so earlier-2026 ECB meetings aren't included).
- US Non-Farm Payrolls (jobs report): COMPUTED, not sourced from a fetched
  list — BLS's Employment Situation release follows a well-established
  "first Friday of the month" rule. Rare holiday-driven shifts aren't
  special-cased; treat this as reliable but not infallible.

Deliberately NOT included: CPI. Its release day isn't a fixed rule like
NFP's, and BLS blocks the page that would confirm exact dates — publishing
a specific date without a verified source would be exactly the false
precision README_forex.md Section 7 forbids. Check
bls.gov/schedule/news_release/cpi.htm manually until this has a real source.

Maintenance: the FOMC/ECB lists need refreshing whenever their official
calendars are updated (both publish roughly a year or more ahead).
"""

from datetime import date, datetime, timedelta

from lib.schemas import EconomicEvent

_FOMC_DECISION_DATES = [
    date(2026, 9, 16),
    date(2026, 10, 28),
    date(2026, 12, 9),
    date(2027, 1, 27),
    date(2027, 3, 17),
    date(2027, 4, 28),
    date(2027, 6, 9),
    date(2027, 7, 28),
    date(2027, 9, 15),
    date(2027, 10, 27),
    date(2027, 12, 8),
]

_ECB_DECISION_DATES = [
    date(2026, 9, 10),
    date(2026, 10, 29),
    date(2026, 12, 17),
]


def _first_friday(year: int, month: int) -> date:
    d = date(year, month, 1)
    offset = (4 - d.weekday()) % 7  # Monday=0 ... Friday=4
    return d + timedelta(days=offset)


def _next_month(d: date) -> date:
    return date(d.year + 1, 1, 1) if d.month == 12 else date(d.year, d.month + 1, 1)


def get_calendar(start: datetime, end: datetime) -> list[EconomicEvent]:
    start_d, end_d = start.date(), end.date()
    events: list[EconomicEvent] = []

    for d in _FOMC_DECISION_DATES:
        if start_d <= d <= end_d:
            events.append(
                EconomicEvent(
                    date=datetime.combine(d, datetime.min.time()),
                    country="US",
                    event="FOMC Rate Decision",
                    impact="HIGH",
                )
            )

    for d in _ECB_DECISION_DATES:
        if start_d <= d <= end_d:
            events.append(
                EconomicEvent(
                    date=datetime.combine(d, datetime.min.time()),
                    country="EU",
                    event="ECB Rate Decision",
                    impact="HIGH",
                )
            )

    cursor = date(start_d.year, start_d.month, 1)
    while cursor <= end_d:
        nfp_date = _first_friday(cursor.year, cursor.month)
        if start_d <= nfp_date <= end_d:
            events.append(
                EconomicEvent(
                    date=datetime.combine(nfp_date, datetime.min.time()),
                    country="US",
                    event="Non-Farm Payrolls (US jobs report)",
                    impact="HIGH",
                )
            )
        cursor = _next_month(cursor)

    events.sort(key=lambda e: e.date)
    return events
