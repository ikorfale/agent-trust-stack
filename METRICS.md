# Agent Trust Stack — Metrics v0

**Version:** 0.1.0‑alpha  
**Last Updated:** 2026‑02‑05

---

## Core Metrics

### PDR (Promise‑Delivery Rate)
- **Definition:** delivered_promises / claimed_promises
- **Adjustments:** decay, impact_weight, recourse_weight
- **Why:** measures reliability over time

### Dependency Impact (DI)
- **Definition:** Σ(workflow_weight × failure_rate × (1 − fallback_score))
- **Why:** captures blast radius when dependencies fail

### MDR (Memory Distortion Rate)
- **Definition:** false_memory_events / interactions
- **Recovery:** corrected_distortions / false_memory_events

### Attestation Chain Score
- **Definition:** Σ(signer_reliability × decay^depth) + chain_bonus − break_penalty
- **Why:** provenance quality over time

---

## Baselines (placeholder)

- PDR target: ≥ 0.9 (critical workflows)
- DI target: ≤ 0.2 (fallback‑aware)
- MDR target: ≤ 0.02
- ChainScore: ≥ 0.7

---

## Data Sources

- Email receipts (message_id + DKIM)
- Task logs / issue trackers
- Incident reports
- User corrections + follow‑ups

---

## Open Questions

- Standard decay curve for PDR?
- How to tier impact_weight objectively?
- How to detect false memory events at scale?
