# Ophaal-Worker

Ierland (`ireland.ie`) en Australië (`smartraveller.gov.au`) weigeren verzoeken uit
datacenters, ook uit de Claude Code-omgeving. Deze Cloudflare Worker haalt die pagina's op
en geeft ze ongewijzigd door. Alleen die twee hosts zijn toegestaan, en alleen met een sleutel.

Let op: volgens `docs/bronnen.md` werkt Ierland vanaf een Worker, maar Australië weigerde ook
Cloudflare. Of Australië via deze Worker lukt, moet de eerste test uitwijzen.

## Eenmalig installeren

Nodig: een (gratis) Cloudflare-account en Node.js.

```bash
cd worker
npx wrangler login
npx wrangler deploy
npx wrangler secret put RELAY_KEY
```

Bij `secret put` kies je zelf een lange willekeurige sleutel. `deploy` toont het adres,
bijvoorbeeld `https://reisadvies-relay.<jouw-naam>.workers.dev`.

## Koppelen aan de checker

```bash
export REISADVIES_RELAY=https://reisadvies-relay.<jouw-naam>.workers.dev
export REISADVIES_RELAY_KEY=<de sleutel>
```

Zonder deze twee variabelen blijven Ierland en Australië op "handmatig nalopen" staan.

## Testen

```bash
curl -s -o /dev/null -w "%{http_code}\n" -H "X-Relay-Key: $REISADVIES_RELAY_KEY" "$REISADVIES_RELAY/?url=https://www.ireland.ie/en/dfa/overseas-travel/advice/turkey/"
```

`200` betekent dat het werkt.
