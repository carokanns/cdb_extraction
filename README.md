# CDB Subset Builder

CLI-verktyg som extraherar öppningsvarianter från [ChessDB](https://www.chessdb.cn/) utifrån en seed-PGN.

## Installation

Aktivera gärna din Conda-miljö först:

```bash
conda activate cdb
```

```bash
python -m pip install -r requirements.txt
```

## Snabbstart

```bash
python cdb_subset_builder.py seed.pgn --out cdb_subset.pgn --max-plies 18 --topn 3 --delta 30
```

För svartrepertoar (en kandidat för svart, flera för vit):

```bash
python cdb_subset_builder.py seed.pgn --out black_rep.pgn --topn-white 4 --topn-black 1 --delta 30
```

## Vanliga flaggor

- `pgn` (krävs): seed-PGN.
- `--out`: output-PGN (default: `cdb_subset.pgn`).
- `--max-plies`: max antal halvdrag inklusive seed.
- `--topn`: max antal kandidater per position.
- `--topn-white`: max antal kandidater när vit står på tur (override för `--topn`).
- `--topn-black`: max antal kandidater när svart står på tur (override för `--topn`).
- `--delta`: behåll drag inom `(bästa score - delta)`, `-1` stänger av.
- `--min-score`: minsta tillåtna score.
- `--min-winrate`: minsta tillåtna winrate.
- `--sleep`: paus mellan API-anrop.
- `--dedupe-global`: ta bort dubletter mellan seed-linjer.

## Output

Genererar en PGN där varje extraherad linje skrivs som ett separat parti.

## Licens

MIT, se [LICENSE](LICENSE).
