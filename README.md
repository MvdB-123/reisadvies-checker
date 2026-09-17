# Reisadvies-checker

Zet het reisadvies van vijf overheden naast elkaar, omgezet naar onze vier
kleurcodes, met de brontekst en de datum erbij. Bedoeld voor de redactie van
Nederland Wereldwijd, om bij een oplopende situatie snel een overzicht te maken
dat zonder bewerking doorgestuurd kan worden.

De strategie achter de tool staat in [STRATEGY.md](STRATEGY.md).

## Wat het is, en wat het niet is

Dit is een **hulpmiddel, geen bron**. De tool haalt op wat andere overheden
publiceren en past er een vaste, zichtbare vertaaltabel op toe. Elk oordeel is
terug te voeren op een letterlijk citaat met een link naar de bronpagina.
Controleer die bron voordat u een overzicht doorstuurt.

De tool **vat niets samen en leidt niets af**. Waar een overheid een niveau niet
kent, staat er "bestaat niet" in plaats van een geraden kleur.

## Het overzicht bekijken

1. Ga in deze repository naar `dist/reisadvies-checker.html`.
2. Klik op **Download raw file** (het pijltje rechtsboven het bestand).
3. Open het gedownloade bestand met een dubbelklik.

Het werkt in elke browser, zonder installatie en zonder internetverbinding. Om
het met een collega te delen stuurt u datzelfde bestand door via Teams of mail.

## Verversen

De adviezen worden **drie keer per dag automatisch** opgehaald: om 05:00, 11:00
en 16:00 UTC. Bovenaan het overzicht staat wanneer dat voor het laatst is gebeurd.

Loopt een situatie op en wilt u nú de laatste stand?

1. Ga naar het tabblad **Actions** in deze repository.
2. Kies links **Reisadviezen verversen**.
3. Klik rechts op **Run workflow**.
4. Wilt u alleen één land verversen, vul dan de landcode in (`TH` voor Thailand,
   `TH,ML` voor meerdere). Leeg laten ververst alles.

Eén land duurt ongeveer tien seconden, alle landen ongeveer een kwartier. Daarna
downloadt u het bestand opnieuw zoals hierboven.

## De mappingtabel aanpassen

`mapping.json` bepaalt welk buitenlands label bij welke Nederlandse kleurcode
hoort. **Dat is redactiewerk, geen techniek.** Het bestand is met de hand te
lezen en aan te passen; bij de eerstvolgende ophaalronde werkt het door in het
overzicht.

Per label legt u vast:

| veld | betekenis |
|---|---|
| `kleur` | onze kleurcode: `groen`, `geel`, `oranje` of `rood` |
| `type` | `letterlijk`, `afgeleid` of `bestaat niet` — zie hieronder |
| `weergave` | hoe het label in het Nederlands op het scherm komt |
| `bronlabel` | hoe die overheid het zelf noemt, in de eigen taal |
| `onderbouwing` | één zin: waarom hoort dit label bij deze kleur? |

- **letterlijk** — die overheid noemt zelf een niveau dat ons niveau dekt.
- **afgeleid** — wij stellen twee schalen gelijk. Dat is een keuze, en het
  overzicht zegt dat er ook bij.
- **bestaat niet** — die overheid kent dit onderscheid niet. Onder `kent_niet`
  legt u uit waarom, zodat het overzicht dat kan tonen.

Komt een overheid met een label dat niet in de tabel staat, dan **raadt de tool
niet**: het overzicht toont "niet in de mappingtabel", en de controle laat de
ophaalronde mislukken totdat de redactie het label heeft geduid.

### Een wijziging meteen zien

Na het aanpassen van `mapping.json` hoeft u niet te wachten op een ophaalronde.
In het tabblad **Actions** kunt u de ronde starten, maar sneller is het om de
tabel opnieuw toe te passen op wat er al ligt:

    python3 bouw.py --hermap

Dat duurt seconden in plaats van een kwartier, omdat het ruwe bronlabel bij elk
niveau bewaard blijft. Het haalt niets op en verandert dus niets aan de datums.

## Hoe het in elkaar zit

| bestand | wat het doet |
|---|---|
| `bronnen/nl.py`, `de.py`, `vk.py`, `vs.py`, `fr.py` | halen per overheid het advies op en leveren het letterlijke bronlabel, het gebied, een citaat en de datum. Vellen geen oordeel. |
| `mapping.json` | het oordeel van de redactie: bronlabel → kleurcode |
| `landen.py` → `data/landen.json` | koppelt de landaanduiding van elke bron aan elkaar (`thailand`, `thailande`, `TH`) |
| `bouw.py` | haalt op, past de mapping toe, schrijft `data/adviezen.json` en het HTML |
| `controle.py` | weigert een ophaalronde die onbruikbaar is |
| `acceptatie.py` | loopt de acceptatiecriteria na op de werkelijke gegevens |
| `test_bouwstenen.py` | tests voor de valkuilen die bij het bouwen echt optraden |
| `sjabloon.html` | het scherm |

Draai `python3 landen.py` opnieuw als er een land bijkomt of als een website zijn
adressen verandert. Dat is zelden nodig.

## De bronnen

| overheid | wat we gebruiken |
|---|---|
| Nederland | de reisadviespagina per land op nederlandwereldwijd.nl |
| Duitsland | de open data van het Auswärtiges Amt |
| Verenigd Koninkrijk | de contentkoppeling van GOV.UK |
| Verenigde Staten | de RSS-feed met reisadviezen van het Department of State |
| Frankrijk | de pagina "Sécurité" per land op diplomatie.gouv.fr |

Alles is openbaar gepubliceerd overheidsmateriaal. Er worden geen
persoonsgegevens verwerkt, en wat u in het zoekveld typt blijft in uw eigen
browser.

### Eigenaardigheden van de bronnen

Dingen die bij het bouwen bleken en die het gedrag van de tool verklaren:

- **De Amerikaanse feed is niet consistent.** Die wordt vanaf meerdere servers
  geserveerd met ongelijke inhoud. Gemeten op 17-09-2026: van de 219 landen
  kwamen er 10 niet in elke ronde voor, waaronder Mali en Noord-Korea. De tool
  haalt de feed daarom drie keer op. Ontbreekt een land dan nog, dan toont het
  overzicht de stand van de vorige ronde, mét de datum daarvan.
- **Duitsland gebruikt twee soorten formuleringen die niet hetzelfde niveau
  uitdrukken.** "Vor Reisen … wird gewarnt" is de formele (Teil-)Reisewarnung;
  "Von Reisen … wird abgeraten" is lichter. Gemeten over de 46 landen met een
  waarschuwingsvlag: 22 gebruiken alleen "gewarnt", 23 gebruiken beide naast
  elkaar. De eerste vorm krijgt rood en het stempel *letterlijk*, de tweede
  oranje met het stempel *afgeleid*. Geen waarschuwing betekent niet "groen".
- **Het VK kent geen groen of geel.** Alleen "advise against all travel" en
  "advise against all but essential travel".
- **Frankrijk geeft geen niveau voor een heel land**, alleen zones op een kaart.
  Behalve als het letterlijk schrijft dat het hele grondgebied in één zone valt;
  dan neemt de tool dat over.
- **De basiskleur op de kaarten van het VK en Frankrijk nemen we niet over.**
  Die kaarten zijn afbeeldingen: de kleur staat niet in de gegevens die zij
  uitleveren. Bovendien zegt de groene legenda van het VK "See our travel advice
  before travelling" — dat is de afwezigheid van een negatief advies, geen
  veiligheidsoordeel zoals onze groen.
- **Een overheid publiceert geen reisadvies over het eigen land.** Bij Duitsland
  als bestemming staat daarom geen Duits advies. Dat is geen storing.

## Nog af te stemmen

- **Geautomatiseerd bevragen van buitenlandse overheidssites.** De tool doet
  maximaal één verzoek per seconde per website, respecteert `robots.txt` en
  meldt zich met een herkenbare afzender. Duitsland en de VS bieden hun gegevens
  uitdrukkelijk als open data aan. Voor de overige drie is het netjes dit intern
  te melden voordat de tool structureel gaat draaien. Zodra dat rond is, hoort
  de naam van het ministerie in de afzender in `bronnen/gedeeld.py`.
- **Eigenaarschap.** Deze repository staat nu op een persoonlijk account. Vóór
  de tool echt gebruikt wordt, moet die naar een team- of BZ-account.
- **Publiceren als webpagina.** Wilt u dat collega's een link openen in plaats
  van een bestand door te sturen, dan kan dat met GitHub Pages. Daarvoor moet de
  repository publiek worden, en dan staat ook de mappingtabel — ons interne
  oordeel — publiek op internet. Dat vraagt akkoord binnen BZ.
