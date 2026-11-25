"""Register van alle bronnen, in de volgorde waarin ze in het overzicht staan."""

from __future__ import annotations

from . import at, au, ca, de, dk, fr, ie, nl, se, uk, us
from .base import Bron

BRONNEN: dict[str, Bron] = {
    b.sleutel: b
    for b in [nl.BRON, uk.BRON, fr.BRON, de.BRON, se.BRON, dk.BRON, ie.BRON, at.BRON, us.BRON, au.BRON, ca.BRON]
}
