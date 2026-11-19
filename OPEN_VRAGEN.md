# Open vragen en beslissingen

Bijgehouden tijdens het bouwen (19-11-2026). Per vraag: wat er speelt, wat ik voorstel, en wat er
nu gebeurt zolang er geen antwoord is. Niets hiervan blokkeert het prototype.

## Toegang tot bronnen

### 1. Nederlandse open-data-API toestaan?
De landpagina's van nederlandwereldwijd.nl verwijzen naar een officiële API op
`opendata.nederlandwereldwijd.nl` (kleurcodes per gebied, kaart). Die host staat niet in de
netwerkregels van de cloudomgeving `reisadvies-checker`.
- **Voorstel**: toevoegen. Een officiële bron is stabieler dan het uitlezen van de webpagina.
- **Nu**: Nederland wordt van de webpagina gelezen; dat werkt voor alle 24 geteste landen.
- **Nodig**: jouw akkoord. Ik kan de netwerkregel voorstellen; jij keurt die goed in de app.

### 2. Zweden: Cloudflare-blokkade
swedenabroad.se houdt Python-verzoeken tegen met een Cloudflare-controle. curl komt (vandaag) wel door.
Die controle omzeilen door een ander programma te gebruiken of een browser na te doen, heb ik bewust
niet gedaan: dat is precies wat de site kennelijk niet wil.
- **Opties**: (a) Zweden handmatig houden; (b) UD vragen om toegang of een feed (andere landen hebben
  er een); (c) bewust kiezen om via curl op te halen, als je dat na overleg acceptabel vindt.
- **Voorstel**: (b), en tot die tijd (a).
- **Nu**: "Handmatig nalopen" met link. De parser is getest en werkt zodra de toegang er is.

### 3. Australië: niet bereikbaar
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

### 5. Mapping nalopen
Zie [MAPPING.md](MAPPING.md). Keuzes die ik heb gemaakt en die een inhoudelijk oordeel zijn:
- **VS niveau 3 "Reconsider travel" → oranje, afgeleid.** Zachter geformuleerd dan "alleen noodzakelijke
  reizen", maar het op één na hoogste niveau. Zelfde keuze voor Australië "Reconsider your need to travel".
- **VK, Duitsland, Zweden: geen kleur als er geen negatief advies is ("bestaat niet").** Zij kennen geen
  onderscheid tussen groen en geel. Groen invullen zou "geen risico" suggereren.
- **Duitsland "situationWarning" → oranje, afgeleid.** De API zegt niet of het om alle of om
  niet-noodzakelijke reizen gaat.
- **Frankrijk: bij alleen kleurkoppen geldt de laagste kleur als "rest van het land", afgeleid.** Dat staat
  alleen op de kaart (een afbeelding). Alternatief: dan helemaal geen landelijk niveau tonen.
- **Vraag**: kloppen deze keuzes met hoe de redactie ernaar kijkt?

### 6. Vertaling van gebiedsteksten
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

### 8. Hoe gaat de redactie het gebruiken?
Nu is het een opdrachtregelprogramma dat een HTML-pagina per land maakt. Opties voor de volgende stap:
- (a) een vaste taak die elk uur een overzicht maakt voor een lijst "landen in de gaten houden",
  met een signaal als een overheid iets wijzigt;
- (b) een kleine webapp waar de redactie een land intypt en direct het overzicht krijgt;
- (c) allebei.
- **Vraag**: wat past bij hoe het team werkt? Waar moet het draaien (eigen server, intern netwerk,
  cloud)? Dat bepaalt ook of Zweden en Australië vanaf daar wél bereikbaar zijn.
