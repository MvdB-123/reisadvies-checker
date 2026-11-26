# Kleurcode-mapping

Hoe de reisadviesniveaus van like-minded landen zich verhouden tot de vier kleurcodes van
Nederland Wereldwijd. Dit bestand is de bron van waarheid voor de vertaalslag die de
Reisadvies-checker maakt. Wijzig hier, niet in de code.

## Statuslabels

Elke cel heeft een status. De tool toont die status altijd bij de uitkomst, zodat de
gebruiker ziet of hij naar een feit of naar een aanname kijkt.

| Status | Betekenis |
| --- | --- |
| `letterlijk` | De officiële formulering van die overheid valt samen met ons niveau. |
| `afgeleid` | Wij maken de vertaalslag; de bron definieert dit niveau niet als officieel niveau. |
| `bestaat niet` | Die overheid kent dit niveau niet. De tool laat de cel leeg met deze notitie en vult hem nooit op met een naburige kleur. |

## Niveau 1 — Groen: geen bijzondere veiligheidsrisico's

| Land | Officiële formulering | Vertaling | Status |
| --- | --- | --- | --- |
| Verenigd Koninkrijk | Take normal precautions | Neem normale voorzorgsmaatregelen | letterlijk |
| Frankrijk | Vigilance normale | Normale waakzaamheid | letterlijk |
| Duitsland | Keine besonderen Sicherheitshinweise | Geen bijzondere veiligheidswaarschuwingen | letterlijk |
| Zweden | Ingen särskilda avrådanden | Geen bijzondere reiswaarschuwingen | letterlijk |
| Denemarken | Vær opmærksom | Wees alert | letterlijk |
| Ierland | Normal precautions | Normale voorzorgsmaatregelen | letterlijk |
| Oostenrijk | Guter Sicherheitsstandard | Goede veiligheidsstandaard | letterlijk |
| Verenigde Staten | Exercise normal precautions | Neem normale voorzorgsmaatregelen | letterlijk |
| Australië | Exercise normal safety precautions | Neem normale veiligheidsmaatregelen | letterlijk |
| Canada | Exercise normal security precautions | Neem normale veiligheidsmaatregelen | letterlijk |

## Niveau 2 — Geel: let op, veiligheidsrisico's

| Land | Officiële formulering | Vertaling | Status |
| --- | --- | --- | --- |
| Verenigd Koninkrijk | — | — | bestaat niet |
| Frankrijk | Vigilance renforcée | Verhoogde waakzaamheid | letterlijk |
| Duitsland | Besondere Vorsicht | Bijzondere voorzichtigheid | afgeleid |
| Zweden | Var extra uppmärksam | Wees extra alert | letterlijk |
| Denemarken | Vær ekstra opmærksom | Wees extra alert | letterlijk |
| Ierland | High degree of caution | Hoge mate van voorzichtigheid | letterlijk |
| Oostenrijk | Sicherheitsrisiko | Veiligheidsrisico | letterlijk |
| Verenigde Staten | Exercise increased caution | Wees extra voorzichtig | letterlijk |
| Australië | Exercise a high degree of caution | Wees zeer voorzichtig | letterlijk |
| Canada | Exercise a high degree of caution | Wees zeer voorzichtig | letterlijk |

Het Verenigd Koninkrijk kent dit niveau officieel niet. Duitsland gebruikt `Besondere
Vorsicht` wel in adviesteksten, maar niet als officieel niveau — vandaar `afgeleid`.

## Niveau 3 — Oranje: alleen noodzakelijke reizen

| Land | Officiële formulering | Vertaling | Status |
| --- | --- | --- | --- |
| Verenigd Koninkrijk | Reconsider your need to travel | Heroverweeg de noodzaak van uw reis | letterlijk |
| Frankrijk | Déconseillé sauf raison impérative | Afgeraden tenzij noodzakelijk | letterlijk |
| Duitsland | Von Reisen wird abgeraten | Reizen wordt afgeraden | letterlijk |
| Zweden | Avrådan från icke nödvändiga resor | Niet-noodzakelijke reizen afgeraden | letterlijk |
| Denemarken | Undgå ikke-nødvendige rejser | Vermijd niet-noodzakelijke reizen | letterlijk |
| Ierland | Avoid non-essential travel | Vermijd niet-noodzakelijke reizen | letterlijk |
| Oostenrijk | Hohes Sicherheitsrisiko | Hoog veiligheidsrisico | letterlijk |
| Verenigde Staten | Reconsider travel | Heroverweeg reizen | letterlijk |
| Australië | Reconsider your need to travel | Heroverweeg de noodzaak van uw reis | letterlijk |
| Canada | Avoid non-essential travel | Vermijd niet-noodzakelijke reizen | letterlijk |

## Niveau 4 — Rood: niet reizen

| Land | Officiële formulering | Vertaling | Status |
| --- | --- | --- | --- |
| Verenigd Koninkrijk | Do not travel | Niet reizen | letterlijk |
| Frankrijk | Formellement déconseillé | Niet reizen | letterlijk |
| Duitsland | Reisewarnung | Reiswaarschuwing / niet reizen | letterlijk |
| Zweden | Avrådan från alla resor | Alle reizen afgeraden | letterlijk |
| Denemarken | Undgå alle rejser | Vermijd alle reizen | letterlijk |
| Ierland | Do not travel | Niet reizen | letterlijk |
| Oostenrijk | Reisewarnung | Reiswaarschuwing / niet reizen | letterlijk |
| Verenigde Staten | Do not travel | Niet reizen | letterlijk |
| Australië | Do not travel | Niet reizen | letterlijk |
| Canada | Avoid all travel | Vermijd alle reizen | letterlijk |

## Bronnen

| Land | Bron |
| --- | --- |
| Nederland | https://www.nederlandwereldwijd.nl/reisadvies |
| Verenigd Koninkrijk | https://www.gov.uk/guidance/about-foreign-commonwealth-development-office-travel-advice |
| Frankrijk | https://www.diplomatie.gouv.fr/fr/que-signifient-les-couleurs-des-cartes-figurant-sur-les-fiches-conseils-aux-voyageurs |
| Duitsland | https://www.auswaertiges-amt.de/de/service/fragenkatalog-node/02-unterschiedhinweisereisewarnung-606066 |
| Zweden | https://www.swedenabroad.se/sv/om-utlandet-för-svenska-medborgare/reseinformation/ |
| Denemarken | https://um.dk/rejse-og-ophold/foer-rejsen/alt-om-rejsevejledninger/ |
| Ierland | https://www.ireland.ie/en/dfa/overseas-travel/advice/ |
| Oostenrijk | https://www.bmeia.gv.at/en/travel-stay/travel-warnings |
| Verenigde Staten | https://travel.state.gov/en/international-travel/travel-advisories.html |
| Australië | https://www.smartraveller.gov.au/consular-services/travel-advice-explained |
| Canada | https://travel.gc.ca/travelling/advisories |

## Geen waarschuwing = groen (besluit 26-11-2026)

Het Verenigd Koninkrijk, Duitsland en Zweden kennen alleen waarschuwen of afraden. Volgens de matrix van NWW
("Uitleg like-minded") geldt hun niveau zonder waarschuwing of afraden als groen. De tool toont dat als groen
met het label `afgeleid` en de toelichting, omdat de bewoording op hun website (bijvoorbeeld "No FCDO advice
against travel") niet letterlijk in de tabel staat. Geel bestaat bij deze landen niet.

## Nog te controleren

- De statuslabels buiten het Verenigd Koninkrijk en Duitsland zijn overgenomen als
  `letterlijk` omdat de oorspronkelijke tabel daar geen voorbehoud bij maakte. Bij twijfel
  per land verifiëren aan de bron.
- Overheden wijzigen hun schaal. Oostenrijk ging op 1 oktober 2025 van zes naar vier
  niveaus; de oorspronkelijke tabel gebruikte nog de oude bewoordingen. Deze mapping
  periodiek tegen de bronnen aanhouden, niet alleen de landenadviezen zelf.

## Nog niet in gebruik

Spanje en Italië staan bewust buiten de werkset. De gegevens blijven hier staan zodat ze
later zonder uitzoekwerk toegevoegd kunnen worden.

| Niveau | Spanje | Italië |
| --- | --- | --- |
| 1 — Groen | Sin riesgo apreciable (Geen specifiek risico) | Normale cautele (Normale voorzorgsmaatregelen) |
| 2 — Geel | Se recomienda viajar con precaución (Verhoogde voorzichtigheid) | Maggiore cautela (Meer voorzichtigheid) |
| 3 — Oranje | Se desaconseja el viaje salvo por razones de necesidad (Vermijd niet-noodzakelijke reizen) | Sconsigliati i viaggi non essenziali (Niet-noodzakelijke reizen afgeraden) |
| 4 — Rood | Se recomienda no viajar (Niet reizen) | Non viaggiare (Niet reizen) |

Bron Spanje: https://www.exteriores.gob.es/es/ServiciosAlCiudadano/Paginas/Recomendaciones-de-viaje.aspx

Voor Italië ontbreekt nog een bronverwijzing.
