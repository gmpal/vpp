"""ENTSO-E Transparency Platform — Belgium day-ahead electricity prices.

Requires a free security token from https://transparency.entsoe.eu/ (register → My Account).
Set the environment variable ENTSOE_API_KEY to enable.  If the key is absent the provider
returns None and callers should fall back to the synthetic price model.

Belgium bidding zone EIC code: 10YBE----------2
Document type A44 = Price Document (day-ahead)
"""
import logging
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

ENTSOE_API = "https://web-api.tp.entsoe.eu/api"
BE_ZONE = "10YBE----------2"
# XML namespace used in ENTSO-E publication documents
NS = "urn:iec62325.351:tc57wg16:451-3:publicationdocument:7:3"


class MarketPriceProvider:
    """Day-ahead EUR/MWh prices for Belgium from ENTSO-E.

    Usage::

        provider = MarketPriceProvider()
        price = await provider.get_current_price()
        # 48.35  (EUR/MWh) — or None if no API key / network error
    """

    def __init__(self):
        self.token = os.environ.get("ENTSOE_API_KEY", "")
        # hour_key (e.g. "2025-04-16T14:00") -> price in EUR/MWh
        self._prices: dict[str, float] = {}
        self._last_fetch_date: Optional[str] = None

    async def get_current_price(self) -> Optional[float]:
        """Return the current hour's day-ahead price in EUR/MWh, or None."""
        if not self.token:
            return None

        now = datetime.now(timezone.utc)
        today = now.strftime("%Y-%m-%d")
        hour_key = now.strftime("%Y-%m-%dT%H:00")

        if self._last_fetch_date != today or hour_key not in self._prices:
            await self._refresh(now)

        price = self._prices.get(hour_key)
        if price is None:
            logger.debug("No ENTSO-E price cached for %s", hour_key)
        return price

    async def _refresh(self, now: datetime) -> None:
        """Fetch today's and tomorrow's day-ahead prices and populate the cache."""
        # Fetch a 48-hour window starting midnight today
        period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        period_end = period_start + timedelta(days=2)

        params = {
            "securityToken": self.token,
            "documentType": "A44",
            "in_Domain": BE_ZONE,
            "out_Domain": BE_ZONE,
            "periodStart": period_start.strftime("%Y%m%d%H%M"),
            "periodEnd": period_end.strftime("%Y%m%d%H%M"),
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(ENTSOE_API, params=params)
                resp.raise_for_status()
        except Exception as exc:
            logger.warning("ENTSO-E fetch failed: %s — market prices unavailable", exc)
            return

        self._parse_xml(resp.text, period_start)
        self._last_fetch_date = now.strftime("%Y-%m-%d")
        logger.info("ENTSO-E cache refreshed — %d hours loaded", len(self._prices))

    def _parse_xml(self, xml_text: str, reference_start: datetime) -> None:
        """Parse ENTSO-E Publication_MarketDocument XML and fill self._prices."""
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            logger.error("ENTSO-E XML parse error: %s", exc)
            return

        for ts in root.findall(f".//{{{NS}}}TimeSeries"):
            period = ts.find(f"{{{NS}}}Period")
            if period is None:
                continue

            interval = period.find(f"{{{NS}}}timeInterval")
            if interval is None:
                continue
            start_el = interval.find(f"{{{NS}}}start")
            if start_el is None or start_el.text is None:
                continue

            # Parse ISO 8601 start time, e.g. "2025-04-15T23:00Z"
            try:
                period_start = datetime.fromisoformat(start_el.text.replace("Z", "+00:00"))
            except ValueError:
                continue

            for point in period.findall(f"{{{NS}}}Point"):
                pos_el = point.find(f"{{{NS}}}position")
                price_el = point.find(f"{{{NS}}}price.amount")
                if pos_el is None or price_el is None:
                    continue
                try:
                    position = int(pos_el.text)  # 1-based hour index
                    price = float(price_el.text)
                except (TypeError, ValueError):
                    continue

                # position 1 = first hour of period
                hour_dt = period_start + timedelta(hours=position - 1)
                hour_key = hour_dt.strftime("%Y-%m-%dT%H:00")
                self._prices[hour_key] = price
