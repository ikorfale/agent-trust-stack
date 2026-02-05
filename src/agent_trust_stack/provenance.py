"""Email-native ledger placeholder."""

from dataclasses import dataclass


@dataclass
class EmailLedger:
    message_id: str
    in_reply_to: str | None
    references: list[str]
    from_addr: str
    to_addr: str
    timestamp: str
    signer: str
    body_hash: str
    headers_hash: str
    signature_chain: list[str]
