# Werkafspraken voor Claude in deze repo

## Eisen
- `docs/eisen-overzicht.md` is leidend. Nooit samenvatten: alleen letterlijk citeren, met een
  DeepL-link voor de vertaling. "Niet opgehaald" altijd zichtbaar als probleem, nooit als "geen risico".
- `docs/bronnen.md`: hoe elke bron wordt opgehaald. Ierland en Australië weigeren datacenters;
  een blokkade wordt niet omzeild (geen ander User-Agent, geen leesproxy).

## Publiceren (toestemming van de eigenaar, 25-11-2026)
- Claude mag eigen pull requests voor deze repo zelf samenvoegen in `main` en daarna de workflow
  "Reisadviezen ophalen en publiceren" (`.github/workflows/site.yml`) starten, en controleert daarna
  of de ronde slaagt.
- Bij een keuze die er inhoudelijk toe doet (wat het overzicht toont, welke bronnen, kosten,
  openbaarheid), eerst de eigenaar vragen.

## Taal
- Communicatie, commits en documentatie in het Nederlands.

## Controleren
- `python -m pytest -q` moet slagen.
- `python -m reisadvies <land>` maakt `uitvoer/<ISO>.html`; `python -m reisadvies site <landen> --uit <map>`
  bouwt de site (zoals de workflow).
