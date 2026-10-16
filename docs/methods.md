# Methods

## 1. Question

How much economic output does a kWh of electricity produce, and how much does that depend on
what the kWh is used for? The repository answers in three parts: across countries (electricity
use against income), by sector in Portugal and Spain (gross value added per kWh from the national
accounts and the energy balance), and for a few specific uses (revenue and value added per kWh
from engineering and price data). A last step asks what one grid connection adds under each use.

The measure throughout is **value added**: output minus everything bought from other producers,
including the electricity. Summed over producers, value added is GDP (before taxes less subsidies
on products). Revenue per kWh is not comparable across uses, because it counts the value of the
inputs again: a tonne of aluminium's price includes the alumina, the anodes and the electricity
bought to make it.

## 2. Across countries

Source: Our World in Data's energy dataset, pinned to commit
`f8de88a4f6f9cab44f1cf606047cbd6c4414042c` of `github.com/owid/energy-data` and checked against
its SHA-256 digest (`config/default.yaml`). Electricity demand per person is OWID's
`electricity_demand_per_capita` (generation plus net imports, from Ember and the Energy Institute).
GDP is OWID's `gdp` column, from the Maddison Project Database, in 2011 international dollars at
purchasing power parity, divided by population. The year is 2022, the latest with GDP. Regional
aggregates (`OWID_` codes) and countries under 250,000 people are dropped.

* `country_floor`: for each income threshold, the number of countries above it and the lowest
  electricity use among them.
* `country_fit`: ordinary least squares of log electricity per person on log GDP per person.
  `country_panel` gives each country's ratio to the fitted line (above one: more electricity than
  countries of its income).
* `country_smelters`: for countries with a sourced primary aluminium output, the electricity that
  smelting takes, `output × MWh per tonne`, as a share of the country's electricity demand, at
  the International Aluminium Institute's 2022 average outside China (15.0 MWh per tonne). Output
  figures and their sources are in the configuration.

The line describes the cloud; it is not a production function. The cross-section cannot say
whether electricity causes income, income causes electricity use, or both follow something else.

## 3. By sector, Portugal and Spain

Sources, all from Eurostat's dissemination API (SDMX 2.1, uncompressed TSV), for 2023:

* `nrg_bal_c`, complete energy balances: final consumption of electricity (`E7000`, GWh), energy
  use, by sector;
* `nama_10_a64`, national accounts by industry (NACE Rev. 2, 64 industries): gross value added
  (`B1G`) at current prices, million euro;
* `nama_10_gdp`: GDP at market prices (`B1GQ`), million euro.

Each sector of the energy balance is matched to the NACE industries it covers (`sectors.mapping`
in the configuration). Iron and steel and non-ferrous metals share NACE division 24, so they are
merged into basic metals. The services sector of the energy balance ("commercial and public
services") covers most of NACE sections G to U, plus repair and installation of machinery (33)
and water supply, sewerage and waste (36 to 39), and leaves out land, water and air transport
(49 to 51), which the balance counts under transport. Its value added is built accordingly, and
imputed rents of owner-occupied dwellings (`L68A`) are removed from it, because they are value
added that uses no electricity. The match is approximate in three small ways: the national
accounts sections used include defence (84.22) and households as employers (T), which the
balance leaves out of services; and the balance counts the non-transport activities of units in
49 to 51 (heating and lighting of stations, for example) under services, while their value added
is removed here in full.

Left out:

* households, which use electricity but produce no value added in the accounts;
* transport, whose energy is overwhelmingly fuel; its value added per kWh of electricity would
  say nothing about electricity;
* the energy industries (electricity, gas, refining), whose own electricity use is not final
  consumption.

The sectors kept account for 69% (Portugal) and 65% (Spain) of final electricity consumption and
for 90% and 87% of gross value added in 2023.

For the sectors kept, the value added per kWh of the whole is the electricity-weighted mean of
the sectors' values,

    VA / E = sum_i (E_i / E) × (VA_i / E_i),

which `economy_value_added` checks. Two economy-wide ratios are also reported: GDP per kWh of
final electricity consumption, the measure behind "dollars of GDP per kWh" comparisons, and
gross value added without imputed rents per kWh of final consumption without households.

Mismatches that remain: mining in the national accounts includes energy extraction (small in
both countries); the energy balance records the electricity of units by their main activity,
the national accounts by establishment or enterprise as each country compiles them.

## 4. Specific uses

See `config/default.yaml` (`uses.items`) for each parameter, its range and its source. For a use
with electricity `k` kWh per unit of output, price `p` per unit and other bought inputs `m` per
unit, at an electricity price `c` per kWh:

    revenue per kWh      = p / k
    value added per kWh  = p / k − c − m / k

The low case pairs the low price with the high electricity per unit and the high other inputs;
the high case the reverse, so the ranges are wide on purpose. Dollar values are converted at the
ECB's 2024 average reference rate. The electricity price is the 2024 average of the Spanish
day-ahead market (OMIE); an industrial consumer also pays network charges and taxes, so this
price flatters the uses for which electricity is the main cost.

Value added is gross: it includes the depreciation of the plant, the servers or the truck. For
capital-intensive uses, net value added (wages, taxes on production and net profit) is much
smaller. `break_even_eur_per_kwh` is value added before electricity, `p / k − m / k`: the
electricity price at which a use's value added falls to zero.

Sources of the parameters (details next to each value in the configuration):

* Green hydrogen: electricity per kg from the Clean Hydrogen Partnership's SRIA key performance
  indicators (2020 state of the art and 2024 targets) and the European Hydrogen Observatory's
  LCOH calculator manual (2025); price proxied by the levelised cost of renewable hydrogen (European Hydrogen
  Observatory, *The European hydrogen market landscape*, November 2025; LCOH calculator manual
  for Spain), with a market price of about 8 EUR/kg as the high case (ACER 2025, as reported by
  pv magazine). Proxying the price by a cost sets profit to zero, so value added is what pays
  for capital and labour.
* Primary aluminium: smelting power from International Aluminium Institute statistics for 2022
  (China 13.4 and the rest of the world 15.0 MWh/t, as quoted in an IAI-hosted report; the
  central 14.1 is their output-weighted mean); LME prices from the World
  Bank's Pink Sheet (February 2026); alumina and carbon use per tonne from Alcoa's Form 10-K for
  2024 and CRU (2023); alumina prices from Alcoa's 2024 results and USGS. Carbon and other
  materials costs are assumptions.
* Battery-electric long-haul truck: energy per km from the ADAC test and Daimler Truck's 2024
  testing tour of the eActros 600 and from the ICCT's 2025 study of fleet use cases (use-case
  averages as reported by trans.info); cost
  per km from the Spanish Ministry of Transport's cost observatory, as reported by Fenadismer and
  the trade press (the ministry's own files could not be read). Revenue is taken as cost.
* Data centre renting space and power: rents per kW of IT capacity from CBRE's European data
  centre releases (June 2025 and June 2026); utilisation, PUE and the low-case rent are
  assumptions.
* Data centre renting out GPUs: H100 rental prices from the Silicon Data index (2025) and
  provider price lists; power per GPU from NVIDIA's DGX H100 user guide (10.2 kW maximum for
  eight GPUs); load and PUE are assumptions.

The electricity price is OMIE's 2024 average for Spain (63.04 EUR/MWh, as reported by Europa
Press) and the exchange rate the ECB's 2024 average (1.0824 USD per EUR).

## 5. One grid connection

`allocation` gives a connection of 100 MW to each use in turn, run for that use's hours a year
(configuration), and reports the electricity used, the value added it produces (range), the
value added per MW of connection, and the country's GDP per kWh before and after. A use can add
value added and still lower the average per kWh; the average is not the criterion.

## 6. Limitations

* Value added measures production, not welfare, and counts nothing for spillovers, for
  employment beyond the wages paid, or for the electricity system's own costs and benefits
  (network reinforcement, flexibility, emissions).
* National accounts record value added where the producing unit is resident. Which country books
  the profit of a multinational's activity depends on how its units are organised and priced;
  the sector figures cannot separate that.
* The cross-country GDP series is in 2011 international dollars, the sector figures in current
  euros, and the per-use figures in 2024 euros. Each comparison stays within one unit.
* Every per-use number is an order-of-magnitude estimate from public parameters, not an
  accounting of any particular plant or company.

## References

* Eurostat. Complete energy balances (`nrg_bal_c`); National accounts aggregates by industry
  (`nama_10_a64`); GDP and main components (`nama_10_gdp`). https://ec.europa.eu/eurostat
* Our World in Data. Energy dataset, https://github.com/owid/energy-data (CC BY 4.0).
* Bolt, J., and van Zanden, J. L. Maddison Project Database. University of Groningen.
