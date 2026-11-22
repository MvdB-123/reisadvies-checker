# Controle van de mapping tegen de uitleg van de overheden

Uitgevoerd op 20-11-2026. Per overheid is de officiële uitleg van de niveaus vergeleken met
[MAPPING.md](MAPPING.md), en waar een overheid zelf een lijst van landen met waarschuwingen publiceert,
zijn onze uitkomsten per land daartegen gelegd.

## Samenvatting

| Overheid | Uitleg gevonden | Mapping klopt | Onafhankelijke controle per land |
|---|---|---|---|
| Nederland | ja: *Reisadviezen en kleurcodes* | ja (referentie) | – |
| Verenigd Koninkrijk | deels: GOV.UK *Foreign travel insurance* | ja | – |
| Frankrijk | ja: FAQ *Quelle est la portée des Conseils aux Voyageurs ?* | ja | – |
| Duitsland | ja: *Reisewarnungen* | **nee, gerepareerd** (zie 1) | 47/47 landen in de waarschuwingslijst kloppen met de API |
| Denemarken | ja: *Alt om rejsevejledninger* | ja | balkkleuren (CSS) kloppen met de titels |
| Oostenrijk | ja: *Reisewarnungen / Sicherheitsstufen* | ja | 41/41 landen in de waarschuwingslijst kloppen |
| Verenigde Staten | nee: uitlegpagina's weigeren geautomatiseerde verzoeken (403) | niveaunamen uit de feed | – |
| Canada | ja: *Risk Levels* op elke landpagina | ja | – |
| Zweden | ja: *Nivåer av avrådan* op elke avrådan-pagina | ja | alle 66 namen op UD's lijst gekoppeld |
| Ierland, Australië | niet gecontroleerd (handmatige bronnen) | – | – |

## Gevonden en gerepareerde fouten

### 1. Duitsland: "afraden" werd gemist (ernstig)
De API van het Auswärtiges Amt heeft een vlag voor afraden (`situationWarning`), maar die wordt bij geen
enkel land gebruikt. Het AA raadt reizen af in de **tekst**. Gevolg: landen waar Duitsland reizen afraadt
zonder formele Reisewarnung verschenen als "geen waarschuwing". Voorbeelden van 20-11-2026:
- **Israël**: *"Von Reisen in andere Landesteile Israels sowie nach Ost-Jerusalem wird abgeraten"* en een
  waarschuwing voor Gaza en de Westelijke Jordaanoever. Werd: geen kleur. Nu: oranje, met rode gebieden.
- **Libanon**: *"Von Reisen in andere Landesteile Libanons wird dringend abgeraten."* Nu: oranje.
- **Venezuela, Nigeria**: idem. Nu: oranje.

Oplossing: de vaste AA-zinnen *"Vor Reisen in/nach … wird gewarnt"* en *"Von Reisen in/nach … wird
(dringend) abgeraten"* worden letterlijk gelezen. De uitleg van het AA zelf: *"Reisewarnungen enthalten
einen dringenden Appell, Reisen … zu unterlassen"* en *"Sicherheitshinweise … kann beinhalten, dass das
Auswärtige Amt von Reisen in ein Land abrät"*.

### 2. Nederland: tips telden als gebieden
Onder een kleurkop (bv. *"Oranje: alleen noodzakelijke reizen"*) staan ook lijsten met tips (*"Blijf niet
langer dan nodig bij checkpoints"*). Die werden als gebied met die kleur getoond. Bij Thailand: 15 in
plaats van 4 gebieden. Nu tellen alleen de lijsten na de vaste zinnen *"Voor de volgende gebieden geldt
kleurcode X:"* en *"Kleurcode X geldt voor:"*.

### 3. Oostenrijk: hoogste regionale niveau werd landelijk (al gerepareerd op 19-11)
*"Sicherheitsstufe 4 (regional)"* in de zijbalk maakte India, Egypte, Kenia, Pakistan en Colombia landelijk
rood. De lijst van Oostenrijk zelf (*Reisewarnung / Region*) bevestigt dat dit regionale waarschuwingen
zijn; alle 41 landen in die lijst kloppen nu.

## Bevestigd per overheid (letterlijke uitleg)

- **Nederland**: groen *"u kunt erheen reizen"*, geel *"let op, er zijn risico's"*, oranje *"alleen
  noodzakelijke reizen … bijvoorbeeld voor de uitvaart van een familielid … of voor uw werk"*, rood *"niet reizen"*.
- **Frankrijk**: vert *vigilance normale*, jaune *vigilance renforcée* (*"compatibles avec le tourisme"*),
  orange *"déconseillés sauf pour des raisons impératives d'ordre professionnel ou familial"*, rouge
  *"formellement déconseillée. Les voyages sont proscrits"*. Komt 1-op-1 overeen met onze vier kleuren.
- **Denemarken**: *"Hvis dit rejsemål er grønt … gult … orange betyder det, at vi fraråder alle
  ikke-nødvendige rejser … (fx presserende familiebesøg, begravelse, vigtig forretningsrejse) … rødt,
  fraråder vi alle rejser"*. In de HTML: groen = `--minimal`, geel = `--low`, oranje = `--medium`,
  rood = `--high`.
- **Oostenrijk**: Stufe 1 *Guter Sicherheitsstandard*, 2 *Sicherheitsrisiko*, 3 *"von nicht unbedingt
  notwendigen Reisen … wird abgeraten"*, 4 *Reisewarnung*.
- **Zweden** (UD, *Nivåer av avrådan*): *icke nödvändiga resor* = *"UD avråder från turist- och
  besöksresor"* (oranje); *alla resor* = ook werkreizen (rood); *uppmaning att lämna landet* (rood).
- **Canada**: *"Avoid non-essential travel … think about your need to travel … based on family or business
  requirements"* = oranje; *"Avoid all travel … You should not travel"* = rood.
- **Verenigd Koninkrijk**: alleen *"advises against all but essential travel"* en *"advises against all
  travel"*. Geen groen/geel: bevestigt "bestaat niet".

### 4. Zweden: rest van het land en vervallen avrådan
Bij de overstap naar regeringen.se bleken drie valkuilen, die nu getest zijn: *"resor till övriga Israel"*
en *"Ryska Federationen (Ryssland)"* werden niet als heel land herkend; de alinea *"Föregående avrådan"*
(de vervallen avrådan) mag niet meetellen; en West-Oekraïne (oranje, milder dan landelijk rood) moet
juist wél getoond worden.

## Wat blijft een oordeel (afgeleid)

- **VS niveau 3 "Reconsider Travel" → oranje.** De uitleg van de VS kon niet worden opgehaald. Het niveau
  is het op één na hoogste; de formulering is zachter dan "alleen noodzakelijke reizen".
- **Duitsland "abgeraten" en "dringend abgeraten" → oranje.** Het AA raadt dan álle reizen af (niet alleen
  niet-noodzakelijke), zonder formele waarschuwing. Inhoudelijk zit dit tussen oranje en rood; "dringend"
  ligt dichter bij rood. We tonen oranje met die kanttekening, plus de letterlijke zin.
- **Frankrijk, alleen kleurkoppen → laagste kleur = rest van het land.** Staat alleen op de kaart.
