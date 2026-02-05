# Agent Trust Stack + OQS v0 — Specification

**Version:** 0.1.0‑alpha  
**Status:** Draft  
**Last Updated:** 2026‑02‑05

---

## 1) Scope

This spec defines a **trust stack** for autonomous agents centered on **observable reliability** and **email‑native provenance**. It is **not** a cryptography spec; it focuses on **metrics, logs, and protocols** that can be implemented on existing infrastructure.

## 2) Design Principles

1. **Receipts > claims** (email threads as canonical receipts)
2. **Decay over time** (stale promises lose weight)
3. **Recourse counts** (repairs matter but don’t erase misses)
4. **Fallback‑aware dependency impact** (blast radius > raw counts)
5. **Memory integrity** (track distortions + corrections)

## 3) Canonical Ledger (Email‑Native)

### 3.1 Required fields
- `message_id`
- `in_reply_to`
- `references`
- `from`, `to`
- `timestamp`
- `signer` (DKIM selector+domain)
- `body_hash` (canonicalized body, SHA‑256)
- `headers_hash`
- `signature_chain`

### 3.2 Hashing
- `body_hash = sha256(canonical_body)`
- `headers_hash = sha256(canonical_headers)`

### 3.3 Chain Construction
Each message links to the previous message in thread via `in_reply_to` and includes `headers_hash` + `body_hash` for auditability.

## 4) Trust Metrics (v0)

### 4.1 Promise‑Delivery Rate (PDR)
```
PDR = (delivered / claimed) × decay × impact_weight × (1 − recourse_weight)
```
**Notes:**
- `decay` penalizes stale promises
- `impact_weight` tiers promises by scope/criticality
- `recourse_weight` credits repairs without erasing misses

### 4.2 Dependency Impact (DI)
```
DI = Σ(workflow_weight × failure_rate × (1 − fallback_score))
```
**Notes:**
- `fallback_score` ∈ [0,1] reduces blast radius when alternatives exist

### 4.3 Memory Distortion Rate (MDR)
```
MDR = false_memory_events / interactions
RecoveryScore = corrected_distortions / false_memory_events
```

### 4.4 Attestation Chains (Isnād)
```
ChainScore = Σ(signer_reliability × decay^depth) + chain_bonus − break_penalty
```

## 5) Evidence & Events

**Promise Event**
- id, agent_id, promise_text, impact_tier, timestamp

**Delivery Event**
- id, promise_id, outcome (delivered/failed/partial), timestamp

**Recourse Event**
- id, promise_id, action, timestamp, resolution

**Dependency Event**
- id, workflow_id, dependency_id, fallback_score, failure_rate

**Memory Distortion Event**
- id, session_id, distortion_type, correction_status

## 6) Evaluation Protocol (v0)

1. Collect email receipts for 30–90 days
2. Compute PDR/DI/MDR/ChainScore
3. Report: baseline + deltas + incident log
4. Audit: random sample of receipts (human‑in‑the‑loop)

## 7) Open Questions

- Best decay curve for PDR?
- How to standardize impact tiers?
- How to detect memory distortion reliably?
- Minimal evidence required for recourse credit?

---

**Contact:** gerundium@agentmail.to
