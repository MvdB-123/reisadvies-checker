# Tests

`python -m pytest` draait alle tests zonder netwerk, op vastgelegde pagina's in `fixtures/`
(gzip, stand 19-11-2026).

- `test_bronnen.py`: per bron de parser op echte pagina's van Turkije en Oekraïne, plus
  regressiegevallen uit de brede steekproef (India bij Oostenrijk, Syrië/China bij Frankrijk, enz.).
- `test_kern.py`: landen koppelen, datums, de mappingtabel en de vergelijking met Nederland.

Fixtures vernieuwen: `python scripts/fixtures.py`. Controleer daarna de verwachte waarden in
`test_bronnen.py` tegen de bronpagina's: reisadviezen veranderen, dus een falende test kan ook
betekenen dat het advies is gewijzigd. Zweden staat achter een Cloudflare-controle; die twee
fixtures zijn eenmalig met de hand opgeslagen.
