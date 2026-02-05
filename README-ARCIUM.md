# Arcium Integration Notes

This note describes how Arcium (confidential MPC compute via MXEs) can be used to compute Trust Stack metrics without exposing private inputs.

## Concept
- Send encrypted event logs to Arcium MXE
- Compute PDR/DI/MDR/ChainScore + HygieneProof gate
- Return proof hash + trust score

## Why it matters
- Avoids exposing sensitive receipts
- Enables verifiable trust outputs

## Next
See `ARCIUM-PLAN.md` for the roadmap.
