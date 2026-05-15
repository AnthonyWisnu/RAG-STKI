# Evaluation Results

Generated at: 2026-05-15T02:49:09.507708+00:00

## Method

RAGAS package is not installed in the active Python environment, so fallback manual evaluation was used.
The fallback rubric checks strategy, language, data availability, citations, required terms, and forbidden terms.

## Metrics

- Total queries: 20
- Passed: 20
- Failed: 0
- Pass rate: 100.00%
- Strategy accuracy: 100.00%
- Language accuracy: 100.00%
- Citation pass rate: 100.00%
- Data availability accuracy: 100.00%
- Average latency: 7351 ms

## Passed Examples

### kg_id_top_scorer_epl
- Question: top skor Premier League 2025-2026
- Strategy: kg_only
- Citations: 8
- Preview: Top hasil dari Knowledge Graph:
1. Erling Haaland (Manchester City Football Club) - 26 gol, 8 assist, 2863 menit
2. Igor Thiago (Brentford Football Club) - 22 gol, 1 assist, 3102 menit
3. Antoine Semenyo (Association Football Club Bournemouth) - 16.0 gol, 4.0 assist, 3083.0 menit
4. João Pedro (Chel

### kg_en_top_scorer_epl
- Question: top scorer Premier League 2025-2026
- Strategy: kg_only
- Citations: 8
- Preview: Top Knowledge Graph results:
1. Erling Haaland (Manchester City Football Club) - 26 goals, 8 assists, 2863 minutes
2. Igor Thiago (Brentford Football Club) - 22 goals, 1 assists, 3102 minutes
3. Antoine Semenyo (Association Football Club Bournemouth) - 16.0 goals, 4.0 assists, 3083.0 minutes
4. João

### kg_id_top_scorer_laliga
- Question: top skor La Liga 2025-2026
- Strategy: kg_only
- Citations: 8
- Preview: Top hasil dari Knowledge Graph:
1. Kylian Mbappé (Real Madrid Club de Fútbol) - 24 gol, 4 assist, 2397 menit
2. Vedat Muriqi (Real Club Deportivo Mallorca S.A.D.) - 22 gol, 1 assist, 2948 menit
3. Ante Budimir (Club Atlético Osasuna) - 17 gol, 0 assist, 2758 menit
4. Ferran Torres (Futbol Club Barce

### kg_en_top_scorer_bundesliga
- Question: top scorer Bundesliga 2025-2026
- Strategy: kg_only
- Citations: 8
- Preview: Top Knowledge Graph results:
1. Harry Kane (FC Bayern München) - 33 goals, 5 assists, 2287 minutes
2. Deniz Undav (Verein für Bewegungsspiele Stuttgart 1893) - 19 goals, 6 assists, 2151 minutes
3. Patrik Schick (Bayer 04 Leverkusen Fußball) - 16 goals, 3 assists, 1898 minutes
4. Serhou Guirassy (Bor

### kg_id_market_value_ramsdale
- Question: berapa nilai pasar Aaron Ramsdale
- Strategy: kg_only
- Citations: 8
- Preview: Nilai pasar terbaru Aaron Ramsdale adalah EUR 12,000,000 pada 2025-12-09.

## Failure Cases

No failed cases in this run.

## Recommendations

- Keep answer synthesis constrained to retrieved rows and citations.
- Treat UCL queries as unsupported negative cases.
- Do not surface unavailable advanced stats such as xG or progressive actions unless real values exist in context.
- Before demo, rerun this script after any prompt or router change.

## Raw Results

See `backend/evaluation/raw_results.json`.
