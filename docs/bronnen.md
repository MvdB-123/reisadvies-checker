# Bronnen per land

Hoe de Reisadvies-checker het actuele reisadvies per overheid ophaalt, en waar dat niet
geautomatiseerd kan. Getest op 19 november 2026.

## Samenvatting

| Land | Ophalen | Opmerking |
| --- | --- | --- |
| Nederland | automatisch | eigen reisadvies, referentiepunt |
| Verenigd Koninkrijk | automatisch | wijzigingsdatum machineleesbaar in de pagina |
| Frankrijk | automatisch | verwijst door, doorverwijzing volgen |
| Duitsland | automatisch | verwijst door, doorverwijzing volgen |
| Denemarken | automatisch | |
| Oostenrijk | automatisch | |
| Canada | automatisch | |
| Verenigde Staten | automatisch via feed | alle landen in één bestand, zie hieronder |
| Australië | via officiële API | nog te testen, zie hieronder |
| Zweden | onbekend | bronadres per land nog uit te zoeken |
| Ierland | **handmatig** | weigert geautomatiseerde verzoeken, geen feed |

## Verenigde Staten — de beste bron

Het Amerikaanse ministerie publiceert alle reisadviezen in één feed:

```
https://travel.state.gov/_res/rss/TAsTWs.xml
```

Eén bestand met 218 landen. Per land staan het niveau met nummer en naam (bijvoorbeeld
`United Arab Emirates - Level 3: Reconsider Travel`), de datum van de laatste wijziging,
een link naar het volledige advies en een omschrijving met de redenen. De gewone
landenpagina's weigeren geautomatiseerde verzoeken, de feed niet.

## Australië — officiële API

Het Australische DFAT biedt een publieke export aan:

```
https://smartraveller.gov.au/destinations-export
```

Let op het ontbrekende `www`. Dit adres staat in de `reisadvies-checker`-omgeving maar is
nog niet getest; `www.smartraveller.gov.au` verbreekt de verbinding bij geautomatiseerde
verzoeken.

## Verenigd Koninkrijk — wijzigingsdatum

De Britse landenpagina's bevatten de laatste wijzigingsdatum in een machineleesbaar veld
(`dateModified`). Dat is precies de datum die het overzicht nodig heeft om te laten zien
hoe vers een advies is.

## Ierland — handmatig

Het Ierse ministerie weigert geautomatiseerde verzoeken en publiceert geen feed of
open-databron. Ierland hoort daarom in het overzicht te verschijnen met een directe link en
de notitie dat de redactie dit zelf moet nalopen — niet met een lege cel die als
"geen risico" gelezen kan worden.

Het verzoek is bewust niet vermomd als dat van een gewone bezoeker. Een BZ-tool hoort zich
aan de keuze van een andere overheid te houden.

## Zweden — nog uit te zoeken

De algemene pagina is bekend, het adrespatroon per land nog niet. Uitzoeken voordat Zweden
in het overzicht komt.
