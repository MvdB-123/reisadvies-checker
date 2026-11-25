"""Gegevensmodel: één genormaliseerd reisadvies per overheid per land."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum


class Kleur(str, Enum):
    """De vier kleurcodes van het Nederlandse reisadvies."""

    GROEN = "groen"
    GEEL = "geel"
    ORANJE = "oranje"
    ROOD = "rood"

    @property
    def ernst(self) -> int:
        return {"groen": 1, "geel": 2, "oranje": 3, "rood": 4}[self.value]


class Soort(str, Enum):
    """Hoe een kleur tot stand komt (zie MAPPING.md)."""

    LETTERLIJK = "letterlijk"  # de overheid kent een niveau met dezelfde betekenis
    AFGELEID = "afgeleid"  # de overheid kent een niveau, maar het past niet 1-op-1
    BESTAAT_NIET = "bestaat niet"  # de overheid maakt dit onderscheid niet


class Status(str, Enum):
    OK = "ok"
    HANDMATIG = "handmatig"  # bron is niet automatisch op te halen: handmatig nalopen
    NIET_GEVONDEN = "niet gevonden"  # bron heeft geen advies voor dit land gevonden
    FOUT = "fout"  # ophalen of uitlezen mislukt
    NVT = "n.v.t."  # het eigen land van die overheid: daar geeft zij geen reisadvies voor


@dataclass
class Niveau:
    """Een niveau zoals de bron het noemt, plus onze vertaling naar een kleur."""

    bronlabel: str  # letterlijk zoals de bron het noemt, bv. "Avoid non-essential travel"
    vertaling: str  # Nederlandse vertaling van het bronlabel
    kleur: Kleur | None  # None als het onderscheid niet bestaat
    soort: Soort
    toelichting: str = ""  # waarom deze kleur (uit de mappingtabel)


@dataclass
class Gebied:
    """Een gebied of plaats met een afwijkend niveau."""

    omschrijving: str  # gebiedsnaam/-omschrijving in de brontaal
    niveau: Niveau
    brontekst: str = ""


@dataclass
class Advies:
    bron: str  # sleutel van de bron, bv. "uk"
    land: str  # ISO 3166-1 alpha-2
    status: Status
    url: str | None = None
    landelijk: Niveau | None = None  # niveau voor (de rest van) het land
    gebieden: list[Gebied] = field(default_factory=list)
    gewijzigd_op: str | None = None  # datum laatste wijziging door de overheid (ISO 8601)
    gewijzigd_label: str = ""  # wat die datum precies is, in de woorden van de bron
    opgehaald_op: str = field(default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds"))
    brontekst: str = ""  # korte letterlijke samenvatting van het advies uit de bron
    melding: str = ""  # foutmelding, of uitleg waarom handmatig

    def to_dict(self) -> dict:
        return asdict(self)
