# Option Pricing Lab enhanced update

This drop-in repository update adds an interactive CRR sandbox, correct American early-exercise logic, editable subjective scenario weights, market-spread interpretation, Greeks, volatility sensitivity, convergence visualization, stronger provenance validation, tests, and a gated GitHub Pages workflow.

## Install
1. Create a backup branch.
2. Copy this package into the repository root, preserving directories.
3. Replace the demonstration CSV values in `data/`.
4. Commit and push to `main`.
5. In GitHub Settings > Pages, select GitHub Actions.

## Local validation
```bash
python -m pip install -r requirements.txt
python scripts/validate_inputs.py
python -m pytest -q
python scripts/build_model.py
python -m http.server 8000 --directory docs
```
Open `http://localhost:8000`. Do not open `docs/index.html` directly because `fetch()` requires an HTTP server.
