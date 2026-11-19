# Bronnen: hoe elke overheid wordt uitgelezen

Onderzocht op 19-11-2026. Per bron: waar de gegevens staan, hoe het niveau herkend wordt, welke
datum we tonen, en de valkuilen. De code staat in `reisadvies/sources/<sleutel>.py`.

Algemeen: we sturen een eerlijke User-Agent (`reisadvies-checker/0.1 (prototype; …)`), doen geen
pogingen om blokkades of bot-controles te omzeilen, en halen per land alleen de pagina's op die
nodig zijn (met 15 minuten cache).

## Nederland (`nl`): referentie

- **Landenlijst**: `https://www.nederlandwereldwijd.nl/reisadvies/sitemap.xml` (226 slugs).
- **Land**: `/reisadvies/<slug>`.
- **Niveau**: "In het kort": *"De kleurcode van/voor het reisadvies voor X is rood"* of *"Voor de
  rest van X geldt kleurcode geel"*. Gebieden: in het accordeon "Regionale risico's" een kop per
  kleur (`<h4>Rood: niet reizen</h4>`) met de lijst *"Voor de volgende gebieden geldt kleurcode rood:"*.
- **Datum**: *"Laatst gewijzigd op: dd-mm-jjjj"*.
- **Let op**: er is ook een officiële open-data-API (`opendata.nederlandwereldwijd.nl`), maar die host
  staat niet in de netwerkregels. Zie OPEN_VRAGEN.md.

## Verenigd Koninkrijk (`uk`): officiële API

- **Landenlijst**: `https://www.gov.uk/api/content/foreign-travel-advice` → `links.children`
  (naam + synoniemen).
- **Land**: `/api/content/foreign-travel-advice/<slug>` (JSON).
- **Niveau**: `details.alert_status`, bv. `avoid_all_travel_to_whole_country`,
  `avoid_all_but_essential_travel_to_parts`. Gebieden: elke zin *"FCDO advises against all (but
  essential) travel to …"* in het deel *Warnings and insurance*, met de kop erboven en een lijst eronder.
- **Datum**: `public_updated_at`.
- **Let op**: het VK kent geen onderscheid groen/geel. Zonder "advise against" geven we bewust géén kleur.

## Frankrijk (`fr`)

- **Landenlijst**: slugs uit `https://www.diplomatie.gouv.fr/fr/conseils-aux-voyageurs`.
- **Land**: `/fr/information-par-pays/<slug>/conseils-aux-voyageurs-securite`.
- **Niveau**: onder "Zones de vigilance":
  1. een zin over het hele land (*"L'ensemble du pays est formellement déconseillé"*, *"Le reste du
     territoire est placé en vigilance renforcée"*). We nemen de kleur direct ná "le reste du
     territoire", anders die ervóór;
  2. koppen per kleur (*"Zones formellement déconseillées (rouge sur la carte)"*, ook zonder "(… carte)").
  Vaste formuleringen: *formellement déconseillé* = rood, *déconseillé sauf raison impérative* =
  oranje, *vigilance renforcée* = geel, *vigilance normale* = groen.
- **Datum**: *"Dernière actualisation le dd/mm/jjjj"* bij de kaart.
- **Let op**: als er alleen kleurkoppen zijn en geen zin over het hele land, staat de kleur voor de
  rest van het land alleen op de kaart (een afbeelding). Bij twee of meer koppen nemen we de laagste
  als landelijk, gelabeld **afgeleid**. Sommige landen (Israël, India, VS, Japan) staan in vrije tekst
  beschreven: dan **niet herkend** met de brontekst.

## Duitsland (`de`): officiële API

- **Landenlijst + niveau**: `https://www.auswaertiges-amt.de/opendata/travelwarning` (alle landen,
  met ISO-code) met vlaggen `warning`, `partialWarning`, `situationWarning`, `situationPartWarning`.
- **Land (details)**: `/opendata/travelwarning/<id>` (HTML-inhoud in JSON).
- **Link**: `https://www.auswaertiges-amt.de/de/service/laender/<id>` stuurt door naar de landpagina.
- **Datum**: `lastModified` (epoch).
- **Let op**: Duitsland kent alleen waarschuwen en afraden. Zonder vlag geven we géén kleur.
  De gebieden bij een gedeeltelijke waarschuwing staan alleen in lopende tekst; we tonen de zinnen
  met "wird gewarnt/abgeraten" letterlijk.

## Zweden (`se`): geblokkeerd

- **Landenlijst**: keuzelijst `<option class="dropdown-option-link" …>` op elke reseinformation-pagina.
  Het doeladres verschilt per land (`…/reseinformation/ambassadens-reseinformation/` of
  `…/reseinformation-om-turkiet/`). De keuzelijst geeft het juiste adres.
- **Niveau**: blok `.notice-block__wrapper--dissuasion` ("Avrådan") met vrije zinnen *"avråder från
  alla resor till …"* (rood) en *"… icke nödvändiga resor till …"* (oranje). Geen blok = geen avrådan.
  "övriga delar av" / "resor till <land>." = hele land.
- **Datum**: *"Beslut om avrådan togs den …"*, anders *"Senast uppdaterad …"*.
- **Let op**: swedenabroad.se laat curl door, maar houdt Python-verzoeken tegen met een Cloudflare-controle
  (HTTP 403, "Just a moment…"). Die omzeilen we niet. De parser is getest op met de hand opgeslagen
  pagina's en werkt zodra de toegang geregeld is. Zie OPEN_VRAGEN.md.

## Denemarken (`dk`)

- **Landenlijst**: keuzelijst `<option data-href="/…/rejsevejledninger/<slug>/">` op
  `https://um.dk/rejse-og-ophold/rejse-til-udlandet/rejsevejledninger`.
- **Niveau**: gekleurde balken `li.travel-guide-accordion__item` met titel (*"Vær opmærksom"*,
  *"Vær ekstra forsigtig"*, *"Vi fraråder alle ikke-nødvendige rejser til"*, *"Vi fraråder alle rejser
  til"*) en ondertitel (gebied). *"Hele landet"* of *"resten af landet"* in de ondertitel = landelijk.
- **Datum**: *"Rejsevejledning opdateret: dd.mm.jjjj"*.
- **Let op**: voor sommige landen (Syrië, Haïti, Mali, Venezuela) geeft Denemarken geen advies
  (*"Vi har ingen rejsevejledning"*) → "niet gevonden". Soms alleen balken voor gebieden: landelijk
  dan "niet herkend".

## Ierland (`ie`): handmatig

`ireland.ie` geeft HTTP 403 op geautomatiseerde verzoeken en heeft geen feed of API. In het overzicht
staat Ierland altijd als "Handmatig nalopen" met link.

## Oostenrijk (`at`)

- **Landenlijst**: `https://www.bmeia.gv.at/reise-services/laender-a-bis-z` → `/reiseinformation/land/<slug>`.
- **Niveau**: gekleurde kaart (`div.card.background-*`) met per niveau *"Regionale Reisewarnung
  (Sicherheitsstufe 4 von 4) gilt für …"*, *"Hohes Sicherheitsrisiko (Sicherheitsstufe 3) …"*,
  *"Sicherheitsrisiko (Sicherheitsstufe 2) gilt im Rest des Landes"*. Drie schrijfwijzen van "Stufe".
- **Datum**: *"Unverändert gültig seit: dd.mm.jjjj"*.
- **Let op**: de zijbalk *"Sicherheitsstufe 4 (regional)"* is het hoogste **regionale** niveau en wordt
  nooit als landelijk niveau gebruikt (in een eerdere versie werd India daardoor landelijk rood).

## Verenigde Staten (`us`): officiële feed

- **Alles in één keer**: `https://travel.state.gov/_res/rss/TAsTWs.xml` (±218 landen): titel met
  niveau, categorie `Threat-Level`, `pubDate` en de volledige onderbouwing in `<description>`.
- **Gebieden**: zinnen *"Do not travel to …"* / *"Reconsider travel to …"* in de beschrijving.
- **Let op**: `Country-Tag` is een **FIPS-code**, geen ISO (`AU` = Oostenrijk, `GM` = Duitsland). We
  koppelen daarom op naam. De gewone landenpagina's weigeren geautomatiseerd ophalen, de feed niet. Voor
  sommige landen (Mexico) staan de gebieden niet in de feed; dan volgt een melding.

## Australië (`au`): handmatig

`smartraveller.gov.au` (zonder www) stuurt alleen door naar `www.smartraveller.gov.au`. Die gaf vanuit
deze omgeving een 502 of time-out, ook met een echte browser. De eerder genoemde API is daardoor niet
getest. Zie OPEN_VRAGEN.md.

## Canada (`ca`)

- **Landenlijst + datum**: tabel op `https://travel.gc.ca/travelling/advisories` (land, niveau, *Last updated*).
- **Niveau**: `div.AdvisoryContainer` met kop *"<gebied> - <niveau>"*; klasse `RegionalAdv` = gebied.
  Niveaus: *normal security precautions*, *high degree of caution*, *avoid non-essential travel*,
  *avoid all travel*.
