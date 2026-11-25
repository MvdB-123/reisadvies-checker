"""Statische site: startpagina met alle landen (zoeken, filteren) en per land het overzicht.

    python -m reisadvies site --uit site/            # alle landen (± 15 minuten)
    python -m reisadvies site --uit site/ TR UA IL   # alleen deze landen

Alles is gewone HTML zonder server: te openen vanaf schijf, een intranet, GitHub Pages of als
Claude-artifact. De startpagina is het bookmarkadres.
"""

from __future__ import annotations

import json
import shutil
import time
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .countries import naam
from .model import Advies, Status
from .report import RECENT_DAGEN, _dagen_geleden, _env, render, samenvatting, verzamel
from .sources import BRONNEN
from .sources import nl as nl_bron

PAUZE_SECONDEN = 0.5  # tussen landen: de overheidsservers niet onnodig belasten


def alle_nl_landen() -> list[str]:
    """De landen waarvoor Nederland een reisadvies heeft: dat is de lijst van de redactie."""
    return sorted(nl_bron.api_index())


def samenvat_rij(iso: str, adviezen: list[Advies], nu: datetime) -> dict:
    som = samenvatting(adviezen)
    bronnen = {}
    recent = []
    for a in adviezen:
        kleur = (
            a.landelijk.kleur.value if a.status == Status.OK and a.landelijk and a.landelijk.kleur else None
        )
        if a.status != Status.OK:
            stand = a.status.value
        elif a.landelijk is None:
            stand = "niet herkend"
        elif a.landelijk.kleur is None:
            stand = "geen kleur"
        else:
            stand = a.landelijk.soort.value
        strengste_gebied = max((g.niveau.kleur.ernst for g in a.gebieden if g.niveau.kleur), default=0)
        bronnen[a.bron] = {
            "kleur": kleur,
            "stand": stand,
            "gebieden": len(a.gebieden),
            "strengste_gebied": strengste_gebied,
            "gewijzigd": a.gewijzigd_op,
        }
        dagen = _dagen_geleden(a.gewijzigd_op, nu.date())
        if dagen is not None and dagen <= RECENT_DAGEN:
            recent.append(BRONNEN[a.bron].naam)
    return {
        "iso": iso,
        "naam": naam(iso, "nl"),
        "zoek": " ".join({naam(iso, "nl"), naam(iso, "en"), iso}).lower(),
        "nl": som["nl_kleur"].value if som["nl_kleur"] else None,
        "bronnen": bronnen,
        "strenger": som["strenger"],
        "strengere_gebieden": som["strengere_gebieden"],
        "handmatig": som["niet_beschikbaar"],
        "recent": recent,
    }


_ERNST = {0: "geen", 1: "groen", 2: "geel", 3: "oranje", 4: "rood"}
_NIET_VERGELIJKEN = {"handmatig", "fout", "n.v.t."}  # ophaalproblemen zijn geen wijziging van het advies


def wijzigingen(vorige: list[dict], nieuwe: list[dict]) -> list[dict]:
    """Wat er per land per overheid veranderd is sinds de vorige ronde: landelijke kleur,
    strengste gebied en aantal gebieden. Een bron die nu of toen niet op te halen was, telt niet."""
    oud = {r["iso"]: r for r in vorige}
    uit = []
    for r in nieuwe:
        v = oud.get(r["iso"])
        if not v:
            continue
        regels = []
        for sleutel, b in r["bronnen"].items():
            a = v["bronnen"].get(sleutel)
            if not a or a["stand"] in _NIET_VERGELIJKEN or b["stand"] in _NIET_VERGELIJKEN:
                continue
            naam_bron = BRONNEN[sleutel].naam
            if a["kleur"] != b["kleur"]:
                regels.append(f"{naam_bron}: landelijk {a['kleur'] or 'geen kleur'} → {b['kleur'] or 'geen kleur'}")
            if a["strengste_gebied"] != b["strengste_gebied"]:
                regels.append(
                    f"{naam_bron}: strengste gebied {_ERNST[a['strengste_gebied']]} → {_ERNST[b['strengste_gebied']]}"
                )
            elif a["gebieden"] != b["gebieden"]:
                regels.append(f"{naam_bron}: aantal afwijkende gebieden {a['gebieden']} → {b['gebieden']}")
        if regels:
            uit.append({"iso": r["iso"], "naam": r["naam"], "regels": regels})
    return uit


def bouw(
    uit: Path,
    landen: list[str] | None = None,
    nu: datetime | None = None,
    log=print,
    vorige: Path | None = None,
) -> Path:
    nu = nu or datetime.now(UTC)
    landen = landen or alle_nl_landen()
    (uit / "landen").mkdir(parents=True, exist_ok=True)
    shutil.copytree(Path(__file__).parent / "static" / "fonts", uit / "fonts", dirs_exist_ok=True)
    rijen = []
    for i, iso in enumerate(landen, 1):
        adviezen = verzamel(iso)
        (uit / "landen" / f"{iso}.html").write_text(
            render(iso, adviezen, nu=nu, terug="../index.html", fonts="../fonts/"), encoding="utf-8"
        )
        rijen.append(samenvat_rij(iso, adviezen, nu))
        log(f"[{i}/{len(landen)}] {iso} {naam(iso)}")
        time.sleep(PAUZE_SECONDEN)
    rijen.sort(key=lambda r: r["naam"])
    vorige_rijen = []
    if vorige and vorige.exists():
        try:
            vorige_rijen = json.loads(vorige.read_text(encoding="utf-8"))
        except ValueError:
            log(f"Vorige ronde ({vorige}) niet leesbaar; geen wijzigingen getoond.")
    gewijzigd = wijzigingen(vorige_rijen, rijen)
    bronnen = [{"sleutel": b.sleutel, "naam": b.naam, "vlag": b.vlag} for b in BRONNEN.values()]
    html = (
        _env()
        .get_template("index.html")
        .render(
            rijen=rijen,
            data=json.dumps({"rijen": rijen, "bronnen": bronnen}, ensure_ascii=False),
            bronnen=bronnen,
            gegenereerd=nu.astimezone(ZoneInfo("Europe/Amsterdam")).strftime("%d-%m-%Y %H:%M"),
            recent_dagen=RECENT_DAGEN,
            gewijzigd=gewijzigd,
            fonts="fonts/",
            vergeleken=bool(vorige_rijen),
        )
    )
    (uit / "index.html").write_text(html, encoding="utf-8")
    (uit / "data.json").write_text(json.dumps(rijen, ensure_ascii=False, indent=1), encoding="utf-8")
    return uit / "index.html"
