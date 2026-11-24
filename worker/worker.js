// Ophaal-tussenlaag voor bronnen die verzoeken uit cloudomgevingen weigeren (Ierland, Australië).
//
// Gebruik: GET https://<worker>/?url=<volledige bron-URL>  met header  X-Relay-Key: <sleutel>
// Alleen de hosts in TOEGESTAAN worden opgehaald; de Worker is dus geen open proxy.
// De sleutel staat als geheim in Cloudflare (wrangler secret put RELAY_KEY).

const TOEGESTAAN = new Set([
  "www.ireland.ie",
  "www.smartraveller.gov.au",
  "smartraveller.gov.au",
]);

const CACHE_SECONDEN = 15 * 60;

export default {
  async fetch(request, env, ctx) {
    if (request.method !== "GET") return new Response("Alleen GET", { status: 405 });
    if (!env.RELAY_KEY || request.headers.get("X-Relay-Key") !== env.RELAY_KEY) {
      return new Response("Geen of verkeerde sleutel", { status: 401 });
    }
    const doel = new URL(request.url).searchParams.get("url");
    let url;
    try {
      url = new URL(doel);
    } catch {
      return new Response("Parameter url ontbreekt of is ongeldig", { status: 400 });
    }
    if (url.protocol !== "https:" || !TOEGESTAAN.has(url.hostname)) {
      return new Response(`Host niet toegestaan: ${url.hostname}`, { status: 403 });
    }

    const cache = caches.default;
    const sleutel = new Request(url.toString());
    const bewaard = await cache.match(sleutel);
    if (bewaard) return bewaard;

    const antwoord = await fetch(url.toString(), {
      headers: {
        "User-Agent": "reisadvies-checker/0.1 (vergelijking reisadviezen)",
        "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
        "Accept-Language": "en",
      },
      redirect: "follow",
    });
    const uit = new Response(antwoord.body, {
      status: antwoord.status,
      headers: {
        "Content-Type": antwoord.headers.get("Content-Type") || "text/html; charset=utf-8",
        "X-Bron-Status": String(antwoord.status),
        "X-Bron-Url": antwoord.url,
        "Cache-Control": `max-age=${CACHE_SECONDEN}`,
      },
    });
    if (antwoord.status === 200) ctx.waitUntil(cache.put(sleutel, uit.clone()));
    return uit;
  },
};
