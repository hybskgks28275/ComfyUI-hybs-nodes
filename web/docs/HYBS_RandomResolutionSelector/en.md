# Random Resolution Selector

Selects a resolution from `config/resolution_combos.json` using `seed % number_of_combos`.

The same seed and configuration produce the same result. The JSON file is reloaded for every execution, and changing it causes the node to run again.

## Inputs

- **seed**: Non-negative value used to choose the resolution.

## Outputs

- **width**: Selected width.
- **height**: Selected height.

Strings in `config/resolution_combos.json` are ignored. Only resolution pairs participate in `seed % candidate_count`; headings do not change pair order, duplicate weighting or the result for the same seed.
