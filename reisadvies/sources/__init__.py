"""Register van alle bronnen, in de volgorde waarin ze in het overzicht staan."""

from __future__ import annotations

from . import at, ca, de, dk, fr, nl, se, uk, us
from .base import Bron

IE = Bron(
    "ie",
    "Ierland",
    "🇮🇪",
    "en",
    "https://www.ireland.ie/en/dfa/overseas-travel/advice/",
    automatisch=False,
    opmerking="ireland.ie weigert geautomatiseerde verzoeken (HTTP 403) en heeft geen feed of API. "
    "Handmatig nalopen via de link.",
)

AU = Bron(
    "au",
    "Australië",
    "🇦🇺",
    "en",
    "https://www.smartraveller.gov.au/destinations",
    automatisch=False,
    opmerking="smartraveller.gov.au geeft vanuit de ophaalomgeving geen antwoord (502/time-out; het "
    "adres zonder www stuurt alleen door naar www). Handmatig nalopen via de link.",
)

BRONNEN: dict[str, Bron] = {
    b.sleutel: b
    for b in [nl.BRON, uk.BRON, fr.BRON, de.BRON, se.BRON, dk.BRON, IE, at.BRON, us.BRON, AU, ca.BRON]
}
