"""Gedeelde bouwstenen voor alle ophalers: netjes ophalen, tekst opschonen, citeren."""

import html
import json
import re
import time
import unicodedata
import urllib.error
import urllib.request

# Wie we zijn, voor de beheerders van de sites die we bevragen. Bewust zonder
# de naam van het ministerie: die claim hoort er pas in als het geautomatiseerd
# bevragen intern is afgestemd (zie README, 'Nog af te stemmen').
AFZENDER = (
    "Reisadvies-checker/0.1 (+https://github.com/MvdB-123/reisadvies-checker)"
)

WACHTTIJD = 1.0  # seconden tussen verzoeken naar dezelfde site
POGINGEN = 3
TIJDSLIMIET = 30

_laatste_verzoek = {}


class OphaalFout(Exception):
    """De bron gaf geen bruikbaar antwoord."""


def _wacht_beleefd(url):
    """Niet sneller dan één verzoek per seconde per site."""
    domein = re.sub(r"^https?://([^/]+).*$", r"\1", url)
    vorige = _laatste_verzoek.get(domein)
    if vorige is not None:
        rust = WACHTTIJD - (time.monotonic() - vorige)
        if rust > 0:
            time.sleep(rust)
    _laatste_verzoek[domein] = time.monotonic()


def haal_tekst(url):
    """Haalt een pagina op. Probeert het een paar keer; geeft anders OphaalFout."""
    laatste_fout = None
    for poging in range(POGINGEN):
        _wacht_beleefd(url)
        verzoek = urllib.request.Request(
            url,
            headers={
                "User-Agent": AFZENDER,
                "Accept-Language": "nl,en;q=0.8,fr;q=0.6,de;q=0.6",
            },
        )
        try:
            with urllib.request.urlopen(verzoek, timeout=TIJDSLIMIET) as antwoord:
                rauw = antwoord.read()
            codering = "utf-8"
            return rauw.decode(codering, errors="replace")
        except urllib.error.HTTPError as fout:
            laatste_fout = f"HTTP {fout.code}"
            if fout.code in (404, 410):
                break  # bestaat niet; opnieuw proberen heeft geen zin
        except Exception as fout:  # netwerk, time-out, DNS
            laatste_fout = str(fout)
        if poging < POGINGEN - 1:
            time.sleep(2 ** poging)
    raise OphaalFout(f"{url}: {laatste_fout}")


def haal_json(url):
    try:
        return json.loads(haal_tekst(url))
    except json.JSONDecodeError as fout:
        raise OphaalFout(f"{url}: ongeldige JSON ({fout})")


def plat(rauwe_html):
    """Maakt van HTML doorlopende tekst, zodat zinspatronen te herkennen zijn."""
    tekst = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", rauwe_html)
    # Next.js zet inhoud als JSON-tekst in de pagina; die ontsnapping terugdraaien.
    tekst = tekst.replace("\\u003c", "<").replace("\\u003e", ">")
    tekst = tekst.replace('\\"', '"').replace("\\n", " ")
    tekst = re.sub(r"<[^>]+>", " ", tekst)
    tekst = html.unescape(tekst)
    tekst = unicodedata.normalize("NFC", tekst)
    tekst = tekst.replace(" ", " ")
    return re.sub(r"\s+", " ", tekst).strip()


def zinnen(tekst):
    """Splitst tekst in zinnen.

    Knipt alleen als er na de punt een hoofdletter of aanhalingsteken volgt, en
    niet vlak na een afkorting. Anders hakken 'z. B.', 'bzw.', 'U.S.' of 'St.
    Louis' een zin doormidden, en juist dan raakt de kern van de waarschuwing
    los van het gebied waar hij over gaat.
    """
    ruw = re.split(
        r"(?<![A-Z]\.)(?<![A-Z][a-z]\.)(?<=[.!?])\s+(?=[A-ZÄÖÜÉÈÀÇ0-9\u201e\u201c\"'])",
        tekst or "")
    return [z.strip() for z in ruw if z.strip()]


def citaat(tekst, max_tekens=300):
    """Kapt een citaat af op een zinsgrens, zonder de betekenis om te draaien.

    Afkappen vlak voor een ontkenning ('niet', 'sauf', 'kein') zou de strekking
    omkeren, dus in dat geval kappen we liever een zin eerder af.
    """
    tekst = re.sub(r"\s+", " ", (tekst or "").strip())
    if not tekst:
        return ""
    if len(tekst) <= max_tekens:
        return tekst

    afgekapt = tekst[:max_tekens]
    grens = max(afgekapt.rfind(". "), afgekapt.rfind("! "), afgekapt.rfind("? "))
    if grens > max_tekens * 0.4:
        afgekapt = afgekapt[: grens + 1]
    else:
        spatie = afgekapt.rfind(" ")
        afgekapt = afgekapt[:spatie] if spatie > 0 else afgekapt

    # Eindigt het fragment vlak voor een ontkenning, dan valt de laatste zin af.
    staart = afgekapt[-60:].lower()
    if re.search(r"\b(niet|geen|nooit|sauf|ne|pas|kein|keine|nicht|not|no)\s*$", staart):
        vorige = max(afgekapt.rfind(". "), afgekapt.rfind("! "), afgekapt.rfind("? "))
        if vorige > 0:
            afgekapt = afgekapt[: vorige + 1]
    return afgekapt.rstrip(" ,;:") + " […]"


# Woorden die in de ene taal wel en in de andere niet in een landsnaam staan.
LIDWOORDEN = {
    "de", "het", "den", "der", "die", "das", "la", "le", "les", "el", "los",
    "the", "of", "and", "en", "und", "et", "du", "des", "di", "da", "van",
    "republiek", "republic", "republique", "republik",
}


def normaliseer(tekst):
    """Maakt landsnamen vergelijkbaar: zonder accenten, leestekens en lidwoorden.

    'São Tomé and Príncipe' en 'Sao Tome and Principe' zijn hetzelfde land; de
    Amerikaanse feed gebruikt beide schrijfwijzen door elkaar.
    """
    if not tekst:
        return ""
    tekst = unicodedata.normalize("NFKD", str(tekst))
    tekst = "".join(t for t in tekst if not unicodedata.combining(t))
    tekst = tekst.lower().replace("&", " en ")
    woorden = [w for w in re.split(r"[^a-z0-9]+", tekst) if w and w not in LIDWOORDEN]
    return "".join(woorden)
