# Test fixtures

The three CSV files hold the Eurostat values the analysis uses for 2023, for Portugal (PT) and
Spain (ES), as returned by Eurostat's SDMX 2.1 dissemination API on 16 October 2026:

* `eurostat_nrg_bal_c_2023.csv`: final consumption of electricity (`E7000`, GWh) by sector of the
  energy balance (`nrg_bal_c`);
* `eurostat_nama_10_a64_2023.csv`: gross value added (`B1G`, current prices, million euro) by
  NACE Rev. 2 industry (`nama_10_a64`);
* `eurostat_nama_10_gdp_2023.csv`: GDP at market prices (`B1GQ`, million euro, `nama_10_gdp`).

They were copied from the API's TSV output and checked by sums: the industry subsectors add up to
total industry, the final-consumption sectors to total final consumption, the manufacturing
divisions to manufacturing, and the sections to total value added. `tests/conftest.py` rebuilds
API-shaped TSV responses from them, so the tests run offline and pin the 2023 figures the article
quotes. Eurostat revises its tables; the Reproduce workflow compares a fresh download with the
committed outputs.

Source: Eurostat (ec.europa.eu/eurostat), reuse authorised under the Commission's reuse policy.
