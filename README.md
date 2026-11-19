# Reisadvies-checker

Haalt per land het actuele reisadvies op bij tien gelijkgestemde overheden, zet het naast het
Nederlandse advies en vertaalt elk niveau via een controleerbare mappingtabel naar onze vier
kleurcodes. Het resultaat is één HTML-pagina per land die de redactie kan nalopen en doorsturen.

Zie [STRATEGY.md](STRATEGY.md) voor het waarom, [BRONNEN.md](BRONNEN.md) voor hoe elke overheid
wordt uitgelezen, [MAPPING.md](MAPPING.md) voor de vertaling naar kleuren en
[OPEN_VRAGEN.md](OPEN_VRAGEN.md) voor beslissingen die nog openstaan.

## Voorbeelden

In [`voorbeelden/`](voorbeelden/) staan overzichten van 19-11-2026 voor Turkije, Oekraïne, Israël en
Kenia. Download een bestand en open het in een browser.

## Gebruik

```bash
pip install -r requirements.txt
```

```bash
python -m reisadvies Turkije
```

Dit schrijft `uitvoer/TR.html` (het overzicht) en `uitvoer/TR.json` (dezelfde gegevens,
machineleesbaar). Landen mogen in het Nederlands of Engels, of als ISO-code; meerdere tegelijk
kan ook (`python -m reisadvies TR UA Israël`).

Overige opdrachten:

```bash
python -m reisadvies bronnen      # welke bronnen, automatisch of handmatig
```

```bash
python -m reisadvies mapping      # MAPPING.md opnieuw genereren na een wijziging in mapping.py
```

```bash
python -m pytest                  # tests op vastgelegde pagina's, zonder netwerk
```

```bash
python scripts/dekking.py         # controleren of alle landnamen van elke bron gekoppeld worden
```

## Wat het overzicht laat zien

- **Kernboodschap**: het Nederlandse niveau, en welke overheden landelijk strenger, gelijk of milder
  zijn, wie strengere adviezen voor gebieden heeft, en wat handmatig nagelopen moet worden.
- **Per overheid**: het landelijke niveau als kleur, met het letterlijke bronlabel, de vertaling
  en het label *letterlijk / afgeleid / bestaat niet*; de afwijkende gebieden; en de datum van de
  laatste wijziging zoals de overheid die zelf noemt (wijzigingen van de afgelopen 7 dagen
  gemarkeerd).
- **Details**: per overheid de brontekst en alle gebieden.

Een bron die niet automatisch kan worden opgehaald, verschijnt altijd als rood omkaderde
**"Handmatig nalopen"** met een directe link, nooit als lege cel. Waar een niveau niet met
zekerheid uit vaste formuleringen te halen is, staat **"Niet herkend"** met de brontekst. De tool
interpreteert geen lopende tekst (zie STRATEGY.md, "Niet aan werken").

## Stand van de bronnen (19-11-2026)

| Overheid | Hoe | Status |
|---|---|---|
| Nederland | webpagina (sitemap + landpagina) | automatisch |
| Verenigd Koninkrijk | GOV.UK Content API (JSON) | automatisch |
| Frankrijk | webpagina | automatisch; soms "niet herkend" (vrije tekst) |
| Duitsland | Auswärtiges Amt Open Data API (JSON) | automatisch |
| Zweden | webpagina | **geblokkeerd** (Cloudflare) → handmatig |
| Denemarken | webpagina | automatisch |
| Ierland | – | **handmatig** (weigert geautomatiseerde verzoeken) |
| Oostenrijk | webpagina | automatisch |
| Verenigde Staten | RSS-feed (alle landen in één keer) | automatisch |
| Australië | – | **handmatig** (onbereikbaar vanuit deze omgeving) |
| Canada | webpagina | automatisch |

In een steekproef van 24 landen (waaronder Oekraïne, Israël, Libanon, Rusland, Mexico, Nigeria
en India) gaven de acht automatische bronnen in 178 van de 189 gevallen (94%) een herkend landelijk
niveau of een expliciet "dit onderscheid bestaat niet". De overige 11: zes keer "niet herkend" bij
Frankrijk (landen die in vrije tekst beschreven staan, zoals Israël, India en de VS), één keer bij
Denemarken, en vier keer "niet gevonden" bij Denemarken (geen advies voor o.a. Syrië en Mali).

## Opbouw

```
reisadvies/
  model.py         Advies, Niveau, Gebied; kleuren en soorten
  mapping.py       de mappingtabel (enige plek met het oordeel bronniveau -> kleur)
  countries.py     landnamen per taal (CLDR via Babel) en koppelen aan bronnamen
  http.py          ophalen met vaste User-Agent, time-outs, herhaalpogingen en cache
  sources/         één module per overheid: index(), parse(), ophalen()
  report.py        vergelijking met Nederland en het HTML-overzicht
  templates/       het HTML-sjabloon
tests/             tests op vastgelegde pagina's (fixtures, gzip)
scripts/           dekkingscontrole en fixtures vernieuwen
```
