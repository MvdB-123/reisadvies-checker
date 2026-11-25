from __future__ import annotations

import re
import traceback
from dataclasses import dataclass, field
from datetime import date

from bs4 import BeautifulSoup

from ..model import Advies, Status


@dataclass
class Bron:
    sleutel: str
    naam: str  # bv. "Verenigd Koninkrijk (FCDO)"
    vlag: str
    taal: str  # CLDR-taal om landnamen te koppelen
    startpagina: str
    automatisch: bool = True
    opmerking: str = ""
    _ophalen: object = field(default=None, repr=False)

    @property
    def eigen_land(self) -> str:
        """ISO-code van het land van deze overheid ('uk' -> 'GB')."""
        return {"uk": "GB"}.get(self.sleutel, self.sleutel.upper())

    def haal(self, iso: str) -> Advies:
        """Haal het advies op. Gooit nooit: fouten worden een Advies met status FOUT."""
        if iso == self.eigen_land:
            return Advies(
                self.sleutel,
                iso,
                Status.NVT,
                url=self.startpagina,
                melding="Eigen land: deze overheid geeft hiervoor geen reisadvies.",
            )
        if not self.automatisch:
            return Advies(self.sleutel, iso, Status.HANDMATIG, url=self.startpagina, melding=self.opmerking)
        try:
            return self._ophalen(iso)  # type: ignore[misc]
        except Exception as e:  # noqa: BLE001 - bewust breed: één bron mag het overzicht niet breken
            return Advies(
                self.sleutel,
                iso,
                Status.FOUT,
                url=self.startpagina,
                melding=f"{type(e).__name__}: {e}",
                brontekst=traceback.format_exc(limit=2),
            )


def soep(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def tekst(el) -> str:
    """Zichtbare tekst met normale spaties."""
    if el is None:
        return ""
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)).strip()


def niet_gevonden(bron: str, iso: str, url: str) -> Advies:
    return Advies(
        bron,
        iso,
        Status.NIET_GEVONDEN,
        url=url,
        melding="Deze overheid heeft (onder deze naam) geen reisadvies voor dit land gevonden.",
    )


_MAANDEN = {
    # nl, fr, de, da, sv, en (afkortingen)
    "januari": 1,
    "februari": 2,
    "maart": 3,
    "april": 4,
    "mei": 5,
    "juni": 6,
    "juli": 7,
    "augustus": 8,
    "augusti": 8,
    "mai": 5,
    "september": 9,
    "oktober": 10,
    "november": 11,
    "december": 12,
    "janvier": 1,
    "février": 2,
    "fevrier": 2,
    "mars": 3,
    "avril": 4,
    "juin": 6,
    "juillet": 7,
    "août": 8,
    "aout": 8,
    "septembre": 9,
    "octobre": 10,
    "novembre": 11,
    "décembre": 12,
    "decembre": 12,
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "maj": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "sept": 9,
    "okt": 10,
    "oct": 10,
    "nov": 11,
    "dec": 12,
    "january": 1,
    "february": 2,
    "march": 3,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "october": 10,
}


def datum(s: str) -> str | None:
    """Herken '20-10-2026', '17.06.2026', '15 septembre 2026', '02 nov. 2026' -> '2026-10-20'."""
    s = s.strip()
    m = re.search(r"(\d{1,2})[-./](\d{1,2})[-./](\d{4})", s)
    if m:
        d, mnd, j = map(int, m.groups())
        return date(j, mnd, d).isoformat()
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return "-".join(m.groups())
    m = re.search(r"(\d{1,2})(?:er)?\s+([A-Za-zéûäåö]+)\.?\s+(\d{4})", s)
    if m:
        mnd = _MAANDEN.get(m.group(2).lower())
        if mnd:
            return date(int(m.group(3)), mnd, int(m.group(1))).isoformat()
    return None
