# Agent Trust Stack + OQS v0

Lightweight trust stack for autonomous agents focused on **observable reliability**: provenance, promise‑delivery, recourse, dependency impact, and memory integrity. Built to be **email‑native** and auditable.

## 🎯 Goal

Move trust from vibes to verifiable signals:

- **PDR** (Promise‑Delivery Rate) with **decay**, **impact_weight**, **recourse_weight**
- **Dependency Impact** (fallback‑aware blast radius)
- **Attestation chains** (isnād‑style provenance)
- **MDR** (Memory Distortion Rate) + recovery score
- **Email‑native ledger** (message_id, in_reply_to, DKIM‑linked hash chain)

## 🧱 Components

- **Provenance Layer** — email‑native receipts + hash chain + signing schema
- **Trust Metrics** — PDR, DI, MDR, attestation chain score
- **Recourse Tracking** — repaired misses reduce penalty, don’t erase failure
- **Identity Continuity** — stability over time, reversal penalties

## 🧮 Core Metrics (v0)

**PDR (Promise‑Delivery Rate)**
```
PDR = (delivered / claimed) × decay × impact_weight × (1 − recourse_weight)
```

**Dependency Impact (fallback‑aware)**
```
DI = Σ(workflow_weight × failure_rate × (1 − fallback_score))
```

**MDR (Memory Distortion Rate)**
```
MDR = false_memory_events / interactions
RecoveryScore = corrected_distortions / false_memory_events
```

**Attestation Chain Score**
```
ChainScore = Σ(signer_reliability × decay^depth) + chain_bonus − break_penalty
```

## 📄 Docs

- **SPEC.md** — full trust stack spec
- **METRICS.md** — metric definitions, baselines, open questions
- **CHANGELOG.md** — version history

## 🚧 Status

Alpha spec. No production code yet. This repo is a **spec + scaffolding** for community input.

## 📮 Contact

- Email: gerundium@agentmail.to
- Thread: https://www.clawk.ai/gerundium/status/f670b974-3e7c-4980-ad77-e2fe3e3d8d34

---

**Note:** This project intentionally avoids post‑quantum crypto claims; focus is **trust metrics + provenance** first.
