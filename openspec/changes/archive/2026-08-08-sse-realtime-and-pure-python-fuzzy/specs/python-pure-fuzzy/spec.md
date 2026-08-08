# python-pure-fuzzy Capability Spec

## Requirements

### REQ-1: Pure-Python Fuzzy Matching Fallback
WHEN neither `rapidfuzzy` nor `thefuzz` is installed in the Python environment, `py/lib/scenario_resolver.py` SHALL compute string similarity ratios using native Python functions without throwing a `RuntimeError` or `ImportError`.
