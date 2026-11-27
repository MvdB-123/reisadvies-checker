"""Register van alle bronnen, in de volgorde waarin ze in het overzicht staan.

Ierland en Australië staan onderaan: die zijn in de cloud niet automatisch op te halen."""

from __future__ import annotations

from . import at, au, ca, de, dk, fr, ie, nl, se, uk, us
from .base import Bron

BRONNEN: dict[str, Bron] = {
    b.sleutel: b
    for b in [nl.BRON, uk.BRON, fr.BRON, de.BRON, us.BRON, se.BRON, dk.BRON, at.BRON, ca.BRON, ie.BRON, au.BRON]
}
