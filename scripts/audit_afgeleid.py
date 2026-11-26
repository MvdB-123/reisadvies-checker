"""Telt per bron en soort waar de tool een niveau 'afleidt' (landelijk of gebied) in plaats van letterlijk overneemt."""
import json, sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from reisadvies.sources import BRONNEN, au, ie
from reisadvies.sources import nl as nl_bron
for m in (ie, au):
    m._geblokkeerd = True

def f(iso):
    out = []
    for sl, b in BRONNEN.items():
        a = b.haal(iso)
        if a.status.value != "ok":
            continue
        if a.landelijk and a.landelijk.soort.value != "letterlijk":
            out.append((iso, sl, "landelijk", a.landelijk.soort.value, a.landelijk.bronlabel[:50]))
        for g in a.gebieden:
            if g.niveau.soort.value != "letterlijk":
                out.append((iso, sl, "gebied", g.niveau.soort.value, g.niveau.bronlabel[:50]))
    return out

with ThreadPoolExecutor(6) as ex:
    res = [r for l in ex.map(f, sorted(nl_bron.api_index())) for r in l]
json.dump(res, open(sys.argv[1], "w"), ensure_ascii=False)
c = Counter((r[1], r[2], r[3], r[4]) for r in res)
for k, v in sorted(c.items(), key=lambda x: (x[0][0], -x[1])): print(v, k)
