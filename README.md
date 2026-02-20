# CDB Subset Builder

Ett litet CLI-verktyg för att bygga en delmängd av öppningslinjer från [ChessDB](https://www.chessdb.cn/) baserat på en seed-PGN.

Skriptet läser en eller flera huvudvarianter i en PGN-fil, expanderar varje position via `queryall`, filtrerar kandidater enligt score/winrate-regler och skriver resultatet till en ny PGN.

## Installation

```bash
python -m pip install -r requirements.txt
```

## Beroenden

- `requests`
- `python-chess`
- `google-api-python-client` (för Gmail-exemplet nedan)
- `google-auth-httplib2` (för Gmail-exemplet nedan)
- `google-auth-oauthlib` (för Gmail-exemplet nedan)

## Snabbstart

```bash
python cdb_subset_builder.py \
  seed.pgn \
  --out cdb_subset.pgn \
  --max-plies 18 \
  --topn 3 \
  --delta 30
```

## Viktiga flaggor

- `pgn` (krävs): seed-PGN med öppningslinjer (positionellt argument).
- `--out`: output-PGN (default: `cdb_subset.pgn`).
- `--max-plies`: max antal halvdrag totalt inklusive seed.
- `--topn`: max antal kandidater per position efter filtrering.
- `--delta`: behåll drag inom `(bästa score - delta)`. Sätt `-1` för att stänga av.
- `--min-score`: kasta drag under given score.
- `--min-winrate`: kasta drag under given winrate (om CDB returnerar winrate).
- `--learn`: skickas till CDB som `learn`-parameter.
- `--queue-unknown`: köar okända positioner med CDB `action=queue`.
- `--sleep`: paus mellan API-anrop för att vara snäll mot tjänsten.
- `--dedupe-global`: ta bort dubletter globalt mellan alla seed-linjer.

## Exempel med hårdare filtrering

```bash
python cdb_subset_builder.py \
  seed.pgn \
  --out subset_strict.pgn \
  --max-plies 22 \
  --topn 2 \
  --delta 20 \
  --min-score 30 \
  --min-winrate 520
```

## Output

Skriptet skriver en PGN där varje genererad linje sparas som ett separat parti.

## Gmail read-only (valfritt)

Om du vill läsa din Gmail från CLI med OAuth (utan lösenord i kod) finns `gmail_reader.py`.

1. Gå till Google Cloud Console.
2. Skapa ett projekt (eller använd ett befintligt).
3. Aktivera **Gmail API**.
4. Skapa OAuth-klient av typen **Desktop app**.
5. Ladda ner JSON-filen och spara den som `gmail_credentials.json` i projektroten.

Installera beroenden:

```bash
python -m pip install -r requirements.txt
```

Första körningen öppnar webbläsaren för inloggning/samtycke och sparar token i `gmail_token.json`.

Lista senaste mejlen:

```bash
python gmail_reader.py list --max-results 10
```

Lista med Gmail-query:

```bash
python gmail_reader.py list --query "newer_than:7d from:example@domain.com"
```

Läs ett specifikt mejl:

```bash
python gmail_reader.py read <MESSAGE_ID>
```

Anpassade sökvägar:

```bash
python gmail_reader.py --credentials path/to/client.json --token path/to/token.json list
```

## Licens

Projektet är licensierat under MIT. Se [LICENSE](LICENSE).
