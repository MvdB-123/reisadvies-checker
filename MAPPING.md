# Mappingtabel

_Gegenereerd uit `reisadvies/mapping.py` met `python -m reisadvies mapping`. Niet met de hand bewerken._

Elke overheid heeft haar eigen niveaus. Deze tabel legt vast welke kleur van het Nederlandse reisadvies we eraan koppelen, en hoe zeker dat is:

- **letterlijk**: de overheid kent een niveau met dezelfde betekenis.
- **afgeleid**: de overheid kent een niveau, maar de criteria wijken af. Nalezen bij twijfel.
- **bestaat niet**: de overheid maakt dit onderscheid niet. We tonen dan géén kleur.

## Nederland

| Bronniveau | Vertaling | Kleur | Soort | Toelichting |
|---|---|---|---|---|
| Groen | Geen bijzondere veiligheidsrisico's | groen | letterlijk | Referentie. |
| Geel | Let op, veiligheidsrisico's | geel | letterlijk | Referentie. |
| Oranje | Alleen noodzakelijke reizen | oranje | letterlijk | Referentie. |
| Rood | Niet reizen | rood | letterlijk | Referentie. |

## Verenigd Koninkrijk

| Bronniveau | Vertaling | Kleur | Soort | Toelichting |
|---|---|---|---|---|
| FCDO advises against all travel | Ontraadt alle reizen | rood | letterlijk |  |
| FCDO advises against all but essential travel | Ontraadt alle niet-noodzakelijke reizen | oranje | letterlijk |  |
| No FCDO advice against travel | Geen negatief reisadvies van de FCDO | — | bestaat niet | Het VK kent geen onderscheid tussen groen en geel: zonder 'advise against' is het advies alleen 'lees de risico's'. Dat kan groen of geel zijn. |

## Frankrijk

| Bronniveau | Vertaling | Kleur | Soort | Toelichting |
|---|---|---|---|---|
| Vigilance normale (vert) | Normale waakzaamheid | groen | letterlijk |  |
| Vigilance renforcée (jaune) | Verhoogde waakzaamheid | geel | letterlijk |  |
| Déconseillé sauf raison impérative (orange) | Afgeraden tenzij dringende reden | oranje | letterlijk |  |
| Formellement déconseillé (rouge) | Uitdrukkelijk afgeraden | rood | letterlijk |  |

## Duitsland

| Bronniveau | Vertaling | Kleur | Soort | Toelichting |
|---|---|---|---|---|
| Reisewarnung | Reiswaarschuwing | rood | letterlijk |  |
| Teilreisewarnung | Reiswaarschuwing voor delen van het land | rood | letterlijk |  |
| Von (nicht notwendigen) Reisen wird abgeraten | Van (niet-noodzakelijke) reizen wordt afgeraden | oranje | afgeleid | Het Auswärtiges Amt geeft dit als 'situationWarning'; de precieze formulering (alle reizen of niet-noodzakelijke reizen) staat in de brontekst. |
| Teilweise Abratung | Voor delen van het land wordt van reizen afgeraden | oranje | afgeleid | Zie 'abraten'. |
| Reise- und Sicherheitshinweise (keine Warnung) | Reis- en veiligheidsinformatie, geen waarschuwing | — | bestaat niet | Duitsland kent alleen waarschuwen/afraden; daaronder geen onderscheid tussen groen en geel. |

## Denemarken

| Bronniveau | Vertaling | Kleur | Soort | Toelichting |
|---|---|---|---|---|
| Vær opmærksom | Wees alert | groen | letterlijk | Groene balk. |
| Vær ekstra forsigtig | Wees extra voorzichtig | geel | letterlijk | Gele balk. |
| Vi fraråder alle ikke-nødvendige rejser | Wij ontraden alle niet-noodzakelijke reizen | oranje | letterlijk | Oranje balk. |
| Vi fraråder alle rejser | Wij ontraden alle reizen | rood | letterlijk | Rode balk. |

## Oostenrijk

| Bronniveau | Vertaling | Kleur | Soort | Toelichting |
|---|---|---|---|---|
| Sicherheitsstufe 1 – Guter Sicherheitsstandard | Goede veiligheid | groen | letterlijk |  |
| Sicherheitsstufe 2 – Sicherheitsrisiko | Veiligheidsrisico | geel | letterlijk |  |
| Sicherheitsstufe 3 – Hohes Sicherheitsrisiko | Hoog veiligheidsrisico; afgeraden tenzij noodzakelijk | oranje | letterlijk |  |
| Sicherheitsstufe 4 – Reisewarnung | Reiswaarschuwing | rood | letterlijk |  |

## Zweden

| Bronniveau | Vertaling | Kleur | Soort | Toelichting |
|---|---|---|---|---|
| UD avråder från alla resor | Ontraadt alle reizen | rood | letterlijk |  |
| UD avråder från icke nödvändiga resor | Ontraadt niet-noodzakelijke reizen | oranje | letterlijk |  |
| Ingen avrådan | Geen negatief reisadvies | — | bestaat niet | Zweden kent alleen 'avrådan'; daaronder geen onderscheid tussen groen en geel. |

## Verenigde Staten

| Bronniveau | Vertaling | Kleur | Soort | Toelichting |
|---|---|---|---|---|
| Level 1: Exercise Normal Precautions | Normale voorzorg | groen | letterlijk |  |
| Level 2: Exercise Increased Caution | Verhoogde voorzichtigheid | geel | letterlijk |  |
| Level 3: Reconsider Travel | Heroverweeg de reis | oranje | afgeleid | 'Reconsider travel' is zachter geformuleerd dan 'alleen noodzakelijke reizen', maar is het op één na hoogste niveau. |
| Level 4: Do Not Travel | Niet reizen | rood | letterlijk |  |

## Canada

| Bronniveau | Vertaling | Kleur | Soort | Toelichting |
|---|---|---|---|---|
| Take normal security precautions | Normale voorzorgsmaatregelen | groen | letterlijk |  |
| Exercise a high degree of caution | Wees zeer voorzichtig | geel | letterlijk |  |
| Avoid non-essential travel | Vermijd niet-noodzakelijke reizen | oranje | letterlijk |  |
| Avoid all travel | Vermijd alle reizen | rood | letterlijk |  |

## Australië

| Bronniveau | Vertaling | Kleur | Soort | Toelichting |
|---|---|---|---|---|
| Exercise normal safety precautions | Normale voorzorg | groen | letterlijk |  |
| Exercise a high degree of caution | Wees zeer voorzichtig | geel | letterlijk |  |
| Reconsider your need to travel | Heroverweeg of de reis nodig is | oranje | afgeleid | Zachter geformuleerd dan 'alleen noodzakelijke reizen'. |
| Do not travel | Niet reizen | rood | letterlijk |  |

## Ierland

| Bronniveau | Vertaling | Kleur | Soort | Toelichting |
|---|---|---|---|---|
| Normal precautions | Normale voorzorg | groen | letterlijk |  |
| High degree of caution | Wees zeer voorzichtig | geel | letterlijk |  |
| Avoid non-essential travel | Vermijd niet-noodzakelijke reizen | oranje | letterlijk |  |
| Do not travel | Niet reizen | rood | letterlijk |  |

