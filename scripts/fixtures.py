"""Testfixtures vernieuwen (Turkije en Oekraïne per bron, plus Frankrijk/Israël).

Gebruik:  python scripts/fixtures.py
Daarna:   python -m pytest   en de verwachte waarden in tests/test_bronnen.py bijwerken
          na controle tegen de bronpagina's. Zweden staat achter een Cloudflare-controle;
          die fixtures zijn eenmalig met de hand opgeslagen en worden hier overgeslagen.
"""

from __future__ import annotations

import gzip
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reisadvies import http
from reisadvies.countries import koppel
from reisadvies.sources import at, ca, de, dk, fr, nl, se, uk, us

F = Path(__file__).resolve().parents[1] / "tests" / "fixtures"


def bewaar(naam: str, data: str) -> None:
    (F / f"{naam}.gz").write_bytes(gzip.compress(data.encode("utf-8"), 9))
    print("bijgewerkt:", naam)


def main() -> None:
    for iso in ["TR", "UA"]:
        bewaar(f"nl_{iso}.html", http.text(koppel(iso, "nl", nl.index())))
        bewaar(f"uk_{iso}.json", json.dumps(http.json(koppel(iso, "en", uk.index()))))
        bewaar(f"fr_{iso}.html", http.text(koppel(iso, "fr", fr.index())))
        bewaar(f"dk_{iso}.html", http.text(koppel(iso, "da", dk.index())))
        bewaar(f"at_{iso}.html", http.text(koppel(iso, "de", at.index())))
        url, _ = koppel(iso, "en", ca.index())
        bewaar(f"ca_{iso}.html", http.text(url))
        bewaar(f"us_{iso}.xml", ET.tostring(koppel(iso, "en", us.index()), encoding="unicode"))
        id_, _ = de.index()[iso]
        bewaar(f"de_{iso}.json", json.dumps(http.json(f"{de.API}/{id_}")["response"][id_]))
    bewaar("fr_IL.html", http.text(koppel("IL", "fr", fr.index())))
    # Regressiegevallen uit de brede steekproef van 19-11-2026
    bewaar("at_IN.html", http.text(koppel("IN", "de", at.index())))
    bewaar("fr_SY.html", http.text(koppel("SY", "fr", fr.index())))
    bewaar("fr_CN.html", http.text(koppel("CN", "fr", fr.index())))
    bewaar("dk_SY.html", http.text(koppel("SY", "da", dk.index())))
    bewaar("dk_PK.html", http.text(koppel("PK", "da", dk.index())))
    bewaar("uk_TH.json", json.dumps(http.json(koppel("TH", "en", uk.index()))))
    bewaar("nl_ZA.html", http.text(koppel("ZA", "nl", nl.index())))
    for iso in ["IL", "NG"]:  # afraden alleen in de tekst
        id_, _ = de.index()[iso]
        bewaar(f"de_{iso}.json", json.dumps(http.json(f"{de.API}/{id_}")["response"][id_]))
    # Zweden via regeringen.se
    bewaar("se_lijst.html", http.text(se.LIJST))
    for iso in ["PS", "IL", "RU", "AE", "UA"]:
        bewaar(f"se_rg_{iso}.html", http.text(koppel(iso, "sv", se.ud_index())))
    # Nederlandse open-data-API
    for iso in ["TR", "TH", "VE"]:
        bewaar(f"nl_api_{iso}.json", json.dumps(http.json(nl.api_index()[iso]["dataurl"] + "?output=json")))


if __name__ == "__main__":
    main()
