# Open vragen en beslissingen

Bijgehouden tijdens het bouwen (19-11-2026). Per vraag: wat er speelt, wat ik voorstel, en wat er
nu gebeurt zolang er geen antwoord is. Niets hiervan blokkeert het prototype.

## Toegang tot bronnen

### 1. Nederlandse open-data-API toestaan? ✔ Opgelost (20-11)
Toegestaan en in gebruik; de webpagina is de terugval.

### 2. Zweden: Cloudflare-blokkade ✔ Opgelost (22-11)
UD publiceert dezelfde avrådan op regeringen.se, met een volledige lijst van landen. Die host is
toegevoegd; Zweden is nu automatisch. swedenabroad.se omzeilen we niet.

### 3. Australië: niet bereikbaar → Worker klaar (24-11), nog te installeren
Zie worker/README.md. Ierland en Australië lopen daarlangs zodra REISADVIES_RELAY is ingesteld;
de parsers volgen als de echte pagina's binnenkomen.

`www.smartraveller.gov.au` gaf vanuit deze omgeving steeds een 502 of time-out, ook met een echte
browser. `smartraveller.gov.au` zonder www stuurt alleen door naar www. De API die de vorige sessie
noemde, is daardoor niet getest.
- **Vraag**: kun jij vanaf je eigen computer of het werknetwerk `https://www.smartraveller.gov.au/destinations`
  openen? Lukt dat wel, dan blokkeert de site waarschijnlijk cloud- of datacenteradressen.
- **Nu**: "Handmatig nalopen" met link.

### 4. Ierland
Weigert geautomatiseerde verzoeken (HTTP 403), geen feed. Mogelijk via contact met DFA.
- **Nu**: "Handmatig nalopen" met link.

## Inhoud en mapping

### 5. Mapping nalopen ✔ Gecontroleerd (20-11), zie CONTROLE.md
Gecontroleerd tegen de uitleg van elke overheid. Echte fouten gevonden en gerepareerd bij Duitsland
(afraden werd gemist), Nederland (tips telden als gebieden) en Zweden. Blijft een oordeel: VS niveau 3 en
Duits "abgeraten" → oranje (afgeleid).

### 6. Vertaling van gebiedsteksten ✔ Gekozen (24-11)
Vertalingen worden in een Claude-sessie gemaakt en vastgelegd in vertalingen.json, per exacte
brontekst. Ontbreekt er een of is de brontekst gewijzigd: alleen een DeepL-link. Zie reisadvies/vertaling.py.

_Oorspronkelijke vraag:_
Niveaus worden vertaald via de mappingtabel (vast en controleerbaar). Gebiedsomschrijvingen en
bronteksten staan in de brontaal (Frans, Duits, Deens, Zweeds, Engels).
- **Opties**: zo laten; of automatisch vertalen (bv. via de Claude API of DeepL), duidelijk gemarkeerd
  als machinevertaling naast de originele tekst.
- **Nodig**: keuze, en voor automatisch vertalen een API-sleutel. Het gaat om openbare teksten.

### 7. Welke dertien overheden?
STRATEGY.md spreekt van dertien overheidswebsites. Spanje en Italië staan bewust buiten de set. De
cloudomgeving bevat elf bronnen (Nederland plus tien).
- **Vraag**: zijn dit alle bedoelde landen, of horen er nog meer bij (bv. Noorwegen, Finland, België,
  Nieuw-Zeeland)? Toevoegen is per bron een module van ±100 regels plus een rij in de mappingtabel.

## Gebruik

### 8. Hoe gaat de redactie het gebruiken? → bookmarkbare site (22-11)
`python -m reisadvies site` maakt een startpagina met alle landen (zoeken, filteren, Enter opent het land)
en per land het overzicht. Open punten: **waar komt hij te staan, en hoe vaak verversen?**
- (a) Claude-artifact (privé link, deelbaar binnen je organisatie): staat nu klaar, maar verversen kost per
  keer een sessie;
- (b) GitHub Actions + GitHub Pages: gratis en automatisch elk uur, maar de pagina is dan openbaar
  (openbare overheidsinformatie, maar wel een keuze);
- (c) een interne server van het ministerie: het meest passend, maar daar heb ik geen toegang toe.
