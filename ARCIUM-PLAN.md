# Arcium Shield for OpenClaw — Project Plan

**Goal:** Add a confidential‑compute layer (Arcium MXE) to the Trust Stack so an agent can publish verifiable trust metrics without exposing sensitive inputs.

## Why Arcium
- MPC‑based confidential compute (MXEs)
- Verifiable outputs without revealing inputs
- Fits Trust Stack: publish proof hash + score, keep receipts private

## MVP Scope

### Inputs (Encrypted)
- Promise events
- Delivery/recourse events
- HygieneProof events
- Minimal metadata for timestamps + versioning

### Compute inside MXE
- PDR / DI / MDR / ChainScore
- HygieneProof gate

### Outputs (Public)
- trust_score
- hygiene_gate_passed
- proof_hash
- timestamp

## Architecture
1. OpenClaw agent aggregates event logs locally
2. Encrypts batch payload → Arcium MXE
3. MXE computes metrics + outputs proof
4. Agent publishes proof + score only

## Open Questions
- Minimal schema for privacy‑preserving receipts
- Proof format verification on-chain or off-chain?
- Rotation policy for hygiene proofs

## Deliverables
- Spec update (Trust Stack + Arcium layer)
- Prototype MXE workflow
- Verification format + example

## References
- Arcium architecture + MXE overview (arcium.com)
