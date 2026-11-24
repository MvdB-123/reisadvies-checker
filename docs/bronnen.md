# Bronnen per land

Hoe de Reisadvies-checker het actuele reisadvies per overheid ophaalt. Getest op
19 november 2026, herzien op 24 november 2026.

## Waar het ophalen vandaan komt, bepaalt wat lukt

De eerste test draaide vanuit een Claude Code-omgeving. Drie bronnen leken toen onbereikbaar
(Ierland en de Verenigde Staten met een 403, Australië met een verbroken verbinding). Dat
lag aan het IP-adres van die omgeving, niet aan de bronnen zelf: vanaf een Cloudflare Worker
werken Ierland en de Verenigde Staten met een gewone aanvraag.

Dat maakt de keuze van de ophaalomgeving een architectuurkeuze, geen detail. Een Worker als
tussenlaag lost twee dingen tegelijk op: de bronnen zijn bereikbaar, en een statische
frontend kan de gegevens ophalen zonder zelf een server nodig te hebben.

## Samenvatting

| Land | Ophalen | Opmerking |
| --- | --- | --- |
| Nederland | direct | eigen reisadvies, referentiepunt |
| Verenigd Koninkrijk | direct | wijzigingsdatum machineleesbaar in de pagina |
| Frankrijk | direct | verwijst door, doorverwijzing volgen |
| Duitsland | direct | verwijst door, doorverwijzing volgen |
| Denemarken | direct | |
| Oostenrijk | direct | |
| Canada | direct | |
| Ierland | direct | lukt niet vanaf elk IP-adres, zie hieronder |
| Verenigde Staten | via feed | alle landen in één bestand, zie hieronder |
| Australië | via leesproxy | blokkeert datacenter-IP's, zie hieronder |
| Zweden | onbekend | bronadres per land nog uit te zoeken |

## Verenigde Staten — de beste bron

Het Amerikaanse ministerie publiceert alle reisadviezen in één feed:

```
https://travel.state.gov/_res/rss/TAsTWs.xml
```

Eén bestand met 218 landen. Per land staan het niveau met nummer en naam (bijvoorbeeld
`United Arab Emirates - Level 3: Reconsider Travel`), de datum van de laatste wijziging,
een link naar het volledige advies en een omschrijving met de redenen. De gewone
landenpagina's weigeren geautomatiseerde verzoeken, de feed niet.

## Australië — blokkeert datacenter-IP's

Smartraveller weigert verbindingen vanaf datacenter-IP's, ook vanaf een Cloudflare Worker.
Een leesproxy (`r.jina.ai`) haalt de pagina dan alsnog op; een gratis sleutel maakt dat
betrouwbaarder. Dat betekent wel dat het verzoek via een externe dienst loopt — voor
openbare reisadviezen verdedigbaar, maar een bewuste keuze en een afhankelijkheid.

DFAT publiceert daarnaast een export op `https://smartraveller.gov.au/destinations-export`
(zonder `www`). Nog niet getest, en mogelijk een schonere route dan de leesproxy.

## Ierland — werkt wel, maar niet overal vandaan

Eerder hier genoteerd als handmatige klus op grond van een 403. Dat was onjuist: vanaf een
andere omgeving werkt een gewone aanvraag. Het niveau staat op `ireland.ie` alleen nog als
tekst in de pagina, niet meer als CSS-class.

Let op bij Ierland: het oude adres `dfa.ie` bestaat nog en geeft keurig een pagina terug,
maar met een bevroren oude stand. Er faalt dan niets zichtbaar — je leest gewoon verouderde
informatie. Een reden te meer om de wijzigingsdatum altijd te tonen.

## Verenigd Koninkrijk — wijzigingsdatum

De Britse landenpagina's bevatten de laatste wijzigingsdatum in een machineleesbaar veld
(`dateModified`). Dat is precies de datum die het overzicht nodig heeft om te laten zien
hoe vers een advies is.

## Zweden — nog uit te zoeken

De algemene pagina is bekend, het adrespatroon per land nog niet. Uitzoeken voordat Zweden
in het overzicht komt.

## Reisadviezen-buddy als voorbeeld

Een collega bouwt binnen NWW al een vergelijkbare tool:
https://github.com/NWW-team/Reisadviezen-buddy (MIT-licentie). Die dekt zeventien bronnen
en heeft de lastige stukken al opgelost. Waardevol om van over te nemen:

- Een Cloudflare Worker als ophaallaag, met een statische frontend erop.
- Per bron een eigen adapter, zodat een gewijzigde website één bestand raakt.
- Een betrouwbaarheidswaarde per uitkomst (hoog, midden, laag, onzeker) naast de kleurcode.
- Bij Australië bewust `Updated:` lezen en niet `Still current at`: die laatste verspringt
  ook bij een controle zonder inhoudelijke wijziging, en zou een advies verser doen lijken
  dan het is.

## Verseheidscontrole — geldt voor elke bron

Een bron die stilstaat faalt niet zichtbaar. Het oude Ierse adres `dfa.ie` geeft nog altijd
keurig een pagina terug, met een bevroren stand van jaren geleden. Oostenrijk wijzigde in
oktober 2025 zijn hele schaal zonder dat daar iets van te merken was aan de pagina's zelf.
Dezelfde fout, verschillende landen — en in beide gevallen leest de gebruiker iets onjuists
zonder dat er een foutmelding is.

Daarom gelden deze eisen voor elke bron, niet voor een enkele:

1. **Geen wijzigingsdatum, geen kleurcode.** Levert een pagina geen datum op, dan toont de
   tool "onzeker — niet vast te stellen hoe actueel dit is", met een link naar de bron.
2. **Een verdacht oude datum krijgt een waarschuwing** naast de kleurcode, zodat de redactie
   ziet dat dit advies al een tijd niet is aangeraakt terwijl er wel iets speelt.
3. **Altijd het huidige adres gebruiken.** Een oud adres dat blijft werken is geen geldige
   bron. Bij twijfel het adres opnieuw verifiëren, niet de uitkomst vertrouwen.
4. **De mapping periodiek tegen de bronnen houden**, niet alleen de landenadviezen. Een
   overheid kan haar hele schaal wijzigen.
