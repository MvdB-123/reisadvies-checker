"""Eén plek voor HTTP: vaste, eerlijke User-Agent, time-outs en een korte cache in het geheugen."""

from __future__ import annotations

import time

import requests

USER_AGENT = "reisadvies-checker/0.1 (prototype; vergelijking reisadviezen)"
TIMEOUT = 30
CACHE_SECONDEN = 15 * 60
POGINGEN = 3  # bij verbindingsfouten; een HTTP-foutcode wordt niet herhaald

_sessie = requests.Session()
_sessie.headers.update({"User-Agent": USER_AGENT})
_cache: dict[str, tuple[float, requests.Response]] = {}



class OphaalFout(Exception):
    def __init__(self, bericht: str, status: int | None = None):
        super().__init__(bericht)
        self.status = status


def get(url: str, *, cache: bool = True) -> requests.Response:
    nu = time.monotonic()
    if cache and url in _cache and nu - _cache[url][0] < CACHE_SECONDEN:
        return _cache[url][1]
    for poging in range(POGINGEN):
        try:
            r = _sessie.get(url, timeout=TIMEOUT)
            break
        except requests.RequestException as e:
            if poging == POGINGEN - 1:
                raise OphaalFout(f"{url}: {type(e).__name__}: {e}") from e
            time.sleep(2 * (poging + 1))
    if r.status_code != 200:
        raise OphaalFout(f"{url}: HTTP {r.status_code}", r.status_code)
    r.encoding = r.encoding or "utf-8"
    if cache:
        _cache[url] = (nu, r)
    return r


def text(url: str) -> str:
    r = get(url)
    # Sommige servers geven geen charset mee; de pagina's zijn allemaal UTF-8.
    return r.content.decode("utf-8", errors="replace")


def json(url: str):
    return get(url).json()
