# Seed List Generator

Generates `count` random 32-bit seed values as a LIST. Values are unique within one generated list.

The node uses a changing execution fingerprint, so each queue run produces a new list.

## Inputs

- **count**: Number of seeds to generate.

## Outputs

- **seed list**: Generated seed values.
- **count**: Number of generated values.
