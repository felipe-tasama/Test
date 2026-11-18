from model import build_results, DOCS
import json
out=build_results(); (DOCS/'model_results.json').write_text(json.dumps(out,indent=2)); print('Exported docs/model_results.json')
