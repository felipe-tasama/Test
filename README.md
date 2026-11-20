# Coca-Cola (KO) Valuation-to-Option Pricing and Greeks Lab

The FIN 450 Modules 4 and 5 lab extends a discounted cash flow (DCF) valuation of The Coca-Cola Company into a five-scenario option payoff analysis, a Cox–Ross–Rubinstein (CRR) pricing model, and a study of the option's risk sensitivities.

[Interactive dashboard](https://felipe-tasama.github.io/Test/) · [Executed notebook](executed.ipynb) · [Source notebook](valuation_option_lab.ipynb) · [Source documentation](data/source_documentation.csv)

## Equity valuation

| Measure | Value |
| --- | ---: |
| KO stock price, November 19, 2026 | $96.09 |
| Student DCF, September 24, 2026 | $84.36 |
| Comparable-company estimate | $83.35 |
| Analyst target median | $100.00 |
| Analyst target mean | $100.27 |
| Analyst target range | $89.00–$112.00 |
| Analyst target standard deviation | $6.13 |
| Analyst target sample and horizon | 11 targets, 12 months |

The DCF and comparable-company estimates are below the stock price, while the median analyst target is above it. The measures reflect different assumptions and valuation dates. The November 19 stock price and September 24 DCF are separate snapshots. [Analyst targets](data/analyst_targets.csv)

## Selected option and inputs

| Measure | Value |
| --- | ---: |
| Option symbol | KO270917C00095000 |
| Type and exercise style | American call |
| Valuation and quote date | November 19, 2026 |
| Expiration | September 17, 2027 |
| Strike | $95.00 |
| Time to maturity | 302 days (0.827397 years) |
| Contract multiplier | 100 shares |
| Risk-free rate | 4.62% |
| Dividend yield | 2.2063% |
| Implied volatility | 22.14% |
| CRR lattice steps | 200 |
| Market bid / ask | $8.60 / $10.55 |
| Quote volume / open interest | 12 / 562 |

Option prices, payoffs, and sensitivities below are quoted per underlying share. Multiply dollar prices by 100 for the corresponding contract amount. [Company and contract inputs](data/company_inputs.csv)

## Option pricing results

| Measure | Value |
| --- | ---: |
| Analyst-scenario discounted expected payoff | $5.1975 |
| American CRR risk-neutral value | $9.0064 |
| Observed market midpoint | $9.5750 |
| Bid–ask spread | $1.9500 |
| Market midpoint less CRR value | $0.5686 |
| European CRR benchmark | $9.006419 |
| American early-exercise premium | $0.000002 |

The analyst estimate discounts payoffs from five stock-price scenarios using subjective weights. The CRR benchmark prices the call under risk-neutral probabilities using spot, strike, maturity, volatility, the risk-free rate, and the dividend yield. The CRR value falls inside the quoted bid–ask spread, and the scenario estimate falls below the bid. The midpoint is a quote reference. The spread, the model assumptions, and the use of 12-month analyst targets for a 302-day option all matter when interpreting the differences.

| Analyst scenario | Quantile | Terminal KO price | Weight | Call payoff | Discounted contribution |
| --- | ---: | ---: | ---: | ---: | ---: |
| Severe bear | 5th | $92.00 | 10% | $0.00 | $0.0000 |
| Bear | 25th | $97.00 | 20% | $2.00 | $0.3850 |
| Base | 50th | $100.00 | 40% | $5.00 | $1.9250 |
| Bull | 75th | $103.00 | 20% | $8.00 | $1.5400 |
| Tail | 95th | $109.00 | 10% | $14.00 | $1.3475 |

The weighted terminal payoff is $5.40. Applying the 0.962496 discount factor yields $5.1975.

## Greeks and validation

| Measure | Value | Finite-difference check | Unit |
| --- | ---: | ---: | --- |
| Delta | 0.590292 | 0.587643 | Option dollars per $1 stock move |
| Gamma | 0.019620 | 0.015992 | Change in delta per $1 stock move |
| Vega | 0.331425 | 0.331417 | Option dollars per 1 percentage point of volatility |
| Theta | −0.014776 | −0.014771 | Option dollars per calendar day elapsed |
| Rho | 0.394738 | 0.394735 | Option dollars per 1 percentage point of the risk-free rate |

A $1 rise in KO gives a delta-only estimate of +$0.590292, a delta–gamma estimate of +$0.600102, and a full repricing result of +$0.595751. For the combined stock, volatility, time, and rate shock, the approximation is +$0.956224 versus +$0.952519 from full repricing. Gamma shows the largest difference between the reported Greek and its finite-difference check. The alternative stock-price bump gives gamma of 0.019415.

The 200-step lattice uses an up factor of 1.014342, a down factor of 0.985861, and a risk-neutral up probability of 0.499946. The American option bounds, delta range, and gamma sign checks pass. CRR values at 25, 50, 100, 200, and 500 steps are $9.059930, $9.007621, $9.009221, $9.006421, and $9.001211, respectively.

## Reproduce the analysis

Run the commands from the repository root. The build exports the model results for the dashboard. The executed notebook shows the saved tables, and the source notebook can be rerun with the CSV inputs.

```bash
python -m pip install -r requirements.txt
python scripts/validate_inputs.py
python -m pytest -q
python scripts/build_model.py
python -m http.server 8000 --directory docs
```

Open [the local dashboard](http://localhost:8000) after starting the server.
