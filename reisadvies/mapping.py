"""De mappingtabel: van de niveaus van elke overheid naar onze vier kleurcodes.

Dit is de enige plek waar het oordeel "welk bronniveau is welke kleur" wordt vastgelegd.
De ophalers herkennen alleen wélk bronniveau er staat (aan vaste formuleringen, vlaggen of
CSS-klassen) en zoeken de kleur hier op. Pas je hier iets aan, draai dan
`python -m reisadvies mapping` om MAPPING.md opnieuw te genereren.

Soorten:
- letterlijk:   de overheid kent een niveau met dezelfde betekenis als onze kleur.
- afgeleid:     de overheid kent een niveau, maar de criteria wijken af; de kleur is onze
                beste vertaling en moet bij twijfel nagelezen worden.
- bestaat niet: de overheid maakt dit onderscheid niet (bv. geen groen/geel). We geven dan
                géén kleur, zodat niemand een lege of groene cel als "geen risico" leest.
"""

from __future__ import annotations

from dataclasses import replace

from .model import Kleur, Niveau, Soort

G, Y, O, R = Kleur.GROEN, Kleur.GEEL, Kleur.ORANJE, Kleur.ROOD
L, A, X = Soort.LETTERLIJK, Soort.AFGELEID, Soort.BESTAAT_NIET


def _n(label: str, vertaling: str, kleur: Kleur | None, soort: Soort, toelichting: str = "") -> Niveau:
    return Niveau(label, vertaling, kleur, soort, toelichting)


MAPPING: dict[str, dict[str, Niveau]] = {
    "nl": {
        "groen": _n("Groen", "Geen bijzondere veiligheidsrisico's", G, L, "Referentie."),
        "geel": _n("Geel", "Let op, veiligheidsrisico's", Y, L, "Referentie."),
        "oranje": _n("Oranje", "Alleen noodzakelijke reizen", O, L, "Referentie."),
        "rood": _n("Rood", "Niet reizen", R, L, "Referentie."),
    },
    "uk": {
        "avoid_all": _n("FCDO advises against all travel", "Ontraadt alle reizen", R, L),
        "avoid_non_essential": _n(
            "FCDO advises against all but essential travel",
            "Ontraadt alle niet-noodzakelijke reizen",
            O,
            L,
        ),
        "geen": _n(
            "No FCDO advice against travel",
            "Geen negatief reisadvies van de FCDO",
            G,
            A,
            "Het VK kent geen niveau groen of geel: de FCDO raadt alleen af of niet. In de tabel van NWW "
            "geldt 'Take normal precautions' (geen afraden) als groen. Geel bestaat bij het VK niet.",
        ),
    },
    "fr": {
        "vert": _n("Vigilance normale (vert)", "Normale waakzaamheid", G, L),
        "jaune": _n("Vigilance renforcée (jaune)", "Verhoogde waakzaamheid", Y, L),
        "orange": _n(
            "Déconseillé sauf raison impérative (orange)",
            "Afgeraden tenzij dringende reden",
            O,
            L,
        ),
        "rouge": _n("Formellement déconseillé (rouge)", "Uitdrukkelijk afgeraden", R, L),
    },
    "de": {
        # Uitleg AA (ReiseUndSicherheit/10.2.8Reisewarnungen): 'Reisewarnungen enthalten einen dringenden
        # Appell, Reisen in ein Land oder eine Region zu unterlassen'; 'Sicherheitshinweise ... kann
        # beinhalten, dass das Auswärtige Amt von Reisen in ein Land abrät.'
        "reisewarnung": _n("Reisewarnung (Vor Reisen ... wird gewarnt)", "Reiswaarschuwing", R, L),
        "teilreisewarnung": _n(
            "Teilreisewarnung (Vor Reisen in ... wird gewarnt)",
            "Reiswaarschuwing voor een deel van het land",
            R,
            L,
        ),
        "dringend_abraten": _n(
            "Von Reisen ... wird dringend abgeraten",
            "Van reizen wordt dringend afgeraden",
            O,
            A,
            "Sterker dan 'abgeraten', zwakker dan een Reisewarnung. Het AA raadt álle reizen af, niet "
            "alleen niet-noodzakelijke; daarom oranje met de kanttekening dat het richting rood gaat.",
        ),
        "abraten": _n(
            "Von Reisen ... wird abgeraten",
            "Van reizen wordt afgeraden",
            O,
            A,
            "Het AA raadt reizen af zonder formele waarschuwing. Ligt het dichtst bij oranje.",
        ),
        "abraten_niet_noodzakelijk": _n(
            "Von nicht notwendigen Reisen ... wird abgeraten",
            "Van niet-noodzakelijke reizen wordt afgeraden",
            O,
            L,
        ),
        "geen": _n(
            "Reise- und Sicherheitshinweise (keine Warnung, kein Abraten)",
            "Reis- en veiligheidsinformatie, geen waarschuwing of afraden",
            G,
            A,
            "Duitsland kent alleen waarschuwen en afraden. In de tabel van NWW geldt 'Keine besonderen "
            "Sicherheitshinweise' (geen waarschuwing of afraden) als groen.",
        ),
    },
    "dk": {
        "opmaerksom": _n("Vær opmærksom", "Wees alert", G, L, "Groene balk."),
        "ekstra_forsigtig": _n("Vær ekstra forsigtig", "Wees extra voorzichtig", Y, L, "Gele balk."),
        "ikke_noedvendige": _n(
            "Vi fraråder alle ikke-nødvendige rejser",
            "Wij ontraden alle niet-noodzakelijke reizen",
            O,
            L,
            "Oranje balk.",
        ),
        "alle": _n("Vi fraråder alle rejser", "Wij ontraden alle reizen", R, L, "Rode balk."),
    },
    "at": {
        "1": _n("Sicherheitsstufe 1 – Guter Sicherheitsstandard", "Goede veiligheid", G, L),
        "2": _n("Sicherheitsstufe 2 – Sicherheitsrisiko", "Veiligheidsrisico", Y, L),
        "3": _n(
            "Sicherheitsstufe 3 – Hohes Sicherheitsrisiko",
            "Hoog veiligheidsrisico; afgeraden tenzij noodzakelijk",
            O,
            L,
        ),
        "4": _n("Sicherheitsstufe 4 – Reisewarnung", "Reiswaarschuwing", R, L),
    },
    "se": {
        "lamna": _n(
            "UD avråder från alla resor och uppmanar svenskar att lämna landet",
            "Ontraadt alle reizen en roept op het land te verlaten",
            R,
            L,
        ),
        "alla": _n("UD avråder från alla resor", "Ontraadt alle reizen", R, L),
        "icke_nodvandiga": _n(
            "UD avråder från icke nödvändiga resor",
            "Ontraadt niet-noodzakelijke reizen",
            O,
            L,
        ),
        "geen": _n(
            "Ingen avrådan",
            "Geen negatief reisadvies",
            G,
            A,
            "Zweden kent alleen 'avrådan'. In de tabel van NWW geldt 'Ingen särskilda avrådanden' (geen "
            "afraden) als groen.",
        ),
    },
    "us": {
        "1": _n("Level 1: Exercise Normal Precautions", "Normale voorzorg", G, L),
        "2": _n("Level 2: Exercise Increased Caution", "Verhoogde voorzichtigheid", Y, L),
        "3": _n(
            "Level 3: Reconsider Travel",
            "Heroverweeg de reis",
            O,
            A,
            "'Reconsider travel' is zachter geformuleerd dan 'alleen noodzakelijke reizen', "
            "maar is het op één na hoogste niveau.",
        ),
        "4": _n("Level 4: Do Not Travel", "Niet reizen", R, L),
    },
    "ca": {
        "normal": _n("Take normal security precautions", "Normale voorzorgsmaatregelen", G, L),
        "high": _n("Exercise a high degree of caution", "Wees zeer voorzichtig", Y, L),
        "non_essential": _n("Avoid non-essential travel", "Vermijd niet-noodzakelijke reizen", O, L),
        "all": _n("Avoid all travel", "Vermijd alle reizen", R, L),
    },
    "au": {
        "1": _n("Exercise normal safety precautions", "Normale voorzorg", G, L),
        "2": _n("Exercise a high degree of caution", "Wees zeer voorzichtig", Y, L),
        "3": _n(
            "Reconsider your need to travel",
            "Heroverweeg of de reis nodig is",
            O,
            A,
            "Zachter geformuleerd dan 'alleen noodzakelijke reizen'.",
        ),
        "4": _n("Do not travel", "Niet reizen", R, L),
    },
    "ie": {
        "normal": _n("Normal precautions", "Normale voorzorg", G, L),
        "high": _n("High degree of caution", "Wees zeer voorzichtig", Y, L),
        "non_essential": _n("Avoid non-essential travel", "Vermijd niet-noodzakelijke reizen", O, L),
        "all": _n("Do not travel", "Niet reizen", R, L),
    },
}


def niveau(bron: str, sleutel: str) -> Niveau:
    """Geef een kopie van het niveau uit de mappingtabel (kopie, zodat niemand de tabel wijzigt)."""
    return replace(MAPPING[bron][sleutel])


def als_markdown() -> str:
    from .sources import BRONNEN

    regels = [
        "# Mappingtabel",
        "",
        (
            "_Gegenereerd uit `reisadvies/mapping.py` met `python -m reisadvies mapping`. "
            "Niet met de hand bewerken._"
        ),
        "",
        (
            "Elke overheid heeft haar eigen niveaus. Deze tabel legt vast welke kleur van het "
            "Nederlandse reisadvies we eraan koppelen, en hoe zeker dat is:"
        ),
        "",
        "- **letterlijk**: de overheid kent een niveau met dezelfde betekenis.",
        "- **afgeleid**: de overheid kent een niveau, maar de criteria wijken af. Nalezen bij twijfel.",
        "- **bestaat niet**: de overheid maakt dit onderscheid niet. We tonen dan géén kleur.",
        "",
    ]
    for sleutel, tabel in MAPPING.items():
        bron = BRONNEN[sleutel]
        regels += [
            f"## {bron.naam}",
            "",
            "| Bronniveau | Vertaling | Kleur | Soort | Toelichting |",
            "|---|---|---|---|---|",
        ]
        for n in tabel.values():
            kleur = n.kleur.value if n.kleur else "—"
            regels.append(f"| {n.bronlabel} | {n.vertaling} | {kleur} | {n.soort.value} | {n.toelichting} |")
        regels.append("")
    return "\n".join(regels)
