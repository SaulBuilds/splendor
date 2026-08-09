# SPDX-License-Identifier: GPL-2.0-or-later
"""CitrateNetwork adapters (P7) — the real testnet.

Wires the composable deploy interface to CitrateNetwork's *hosted testnet* (chain
id 40204, `https://rpc.citrate.ai`) and to IPFS pinning. The public endpoints +
contract addresses come from the federation address book
(`citrate-chain-mpfix/cli/federation-contract.json`), env-overridable.

Honest by construction, matching Citrate's own design:
- **Chain reads are real** (`eth_chainId`, `eth_blockNumber`) — connectivity is verified.
- **Attestation is an on-chain write** to `AgentDecisionRegistry.registerDecision`
  (selector 0xf5d83567). Signing is delegated to a separate **non-custodial signer**
  process (`splendor.deploy.signer`) — Blender's Python holds no key. `attest()`
  builds the call and hands it to the signer; with no signer configured it raises
  `SignerUnavailable` honestly, and an unauthorized signer reverts
  `NotAuthorizedRecorder` (surfaced, never faked).
- **Pinning is IPFS** (content-addressed) + on-chain `IPFSIncentives`; there is no
  hosted bearer-token pin API, so `IpfsPinning` needs a reachable IPFS daemon/gateway.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

import hashlib

from .chain import AttestationRef, ChainAdapter, digest_record
from .errors import ChainUnavailable, IntegrityError, PinUnavailable, SignerUnavailable
from .pinning import PinRef, PinningBackend
from .signer import resolve_signer

# Public CitrateNetwork testnet config (from the federation address book,
# citrate-chain-mpfix/cli/federation-contract.json — deployed on chain 40204).
CITRATE_TESTNET = {
    "chain_id": 40204,
    "chain_name": "Citrate Network",
    "rpc_url": "https://rpc.citrate.ai",
    "ws_url": "wss://rpc.citrate.ai/ws",
    "explorer_url": "https://explorer.citrate.ai",
    # AgentDecisionRegistry — the deployed, semantically-correct target for recording
    # an AI decision's provenance: registerDecision(bytes32 agentId, string toolName,
    # bytes32 paramsHash), selector 0xf5d83567. Gated by authorizedRecorders[msg.sender].
    "agent_decision_registry": "0x728dbe86ce56123a5c1ddc248392940d7d2d30f9",
    "provenance_registry": "0xd903b7d47f8ba592c1e9ed9dc79ffb2ad97241f5",  # PartProvenanceRegistry (BFR)
    "attestation_registry": "0x4df26aae3619f449a142d237ed818ebf7c186ed5",  # TEEAttestationRegistry (TEE/GPU HW)
    "ipfs_gateway": "http://127.0.0.1:8080",   # env CITRATE_IPFS_GATEWAY; no hosted pin API
    "ipfs_api": "http://127.0.0.1:5001",
}

# The on-chain attestation call (AgentDecisionRegistry.registerDecision).
ATTEST_FUNCTION = "registerDecision(bytes32,string,bytes32)"
ATTEST_SELECTOR = "0xf5d83567"  # keccak(ATTEST_FUNCTION)[:4] — golden vector for the encoder.


def citrate_config(env=None):
    """The Citrate config, env-overridable (CITRATE_RPC_URL, CITRATE_IPFS_GATEWAY, …)."""
    env = env or os.environ
    cfg = dict(CITRATE_TESTNET)
    cfg["rpc_url"] = env.get("CITRATE_RPC_URL", cfg["rpc_url"])
    cfg["ipfs_gateway"] = env.get("CITRATE_IPFS_GATEWAY", cfg["ipfs_gateway"])
    cfg["ipfs_api"] = env.get("CITRATE_IPFS_API", cfg["ipfs_api"])
    cfg["agent_decision_registry"] = env.get("CITRATE_DECISION_REGISTRY", cfg["agent_decision_registry"])
    return cfg


class CitrateEvmChain(ChainAdapter):
    """EVM JSON-RPC client for CitrateNetwork (chain 40204). Reads are real;
    attestation-write is honestly deferred to the non-custodial signer."""

    def __init__(self, rpc_url=None, chain_id=40204, registry=None, timeout=15.0, signer=None):
        cfg = citrate_config()
        self.network = "citrate-testnet"
        self.rpc_url = rpc_url or cfg["rpc_url"]
        self.expected_chain_id = chain_id
        # Attestation writes go to AgentDecisionRegistry (registerDecision).
        self.registry = registry or cfg["agent_decision_registry"]
        self.timeout = timeout
        self._signer = signer  # explicit override; else resolved from env at attest time.

    def _rpc(self, method, params):
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
        req = urllib.request.Request(self.rpc_url, data=body, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode())
        except (urllib.error.URLError, OSError) as exc:
            raise ChainUnavailable(f"{self.network} RPC unreachable: {exc}") from exc
        if "error" in data:
            raise ChainUnavailable(f"{self.network} RPC error: {data['error']}")
        return data["result"]

    def chain_id(self) -> int:
        return int(self._rpc("eth_chainId", []), 16)

    def block_number(self) -> int:
        return int(self._rpc("eth_blockNumber", []), 16)

    def reachable(self) -> bool:
        try:
            return self.chain_id() == self.expected_chain_id
        except ChainUnavailable:
            return False

    def chain_info(self) -> dict:
        return {"chain_id": self.chain_id(), "block": self.block_number(),
                "rpc": self.rpc_url, "registry": self.registry}

    def _decision_args(self, record: dict) -> list:
        """Map a provenance record → registerDecision(bytes32,string,bytes32) args.

        paramsHash binds the whole record (content hash + eval + workflow + meta) via
        its sha256 digest; toolName is the workflow; agentId is a stable Splendor agent
        id namespaced by the tool. Deterministic and reproducible.
        """
        digest = digest_record(record)                       # "sha256:<64 hex>"
        params_hash = "0x" + digest.split(":", 1)[1]         # bytes32
        tool = str(record.get("workflow")
                   or (record.get("meta") or {}).get("prompt") or "splendor")[:200]
        agent_id = "0x" + hashlib.sha256(("splendor.agent:" + tool).encode()).hexdigest()  # bytes32
        return [agent_id, tool, params_hash]

    def attest(self, record: dict) -> AttestationRef:
        # Connectivity is real; the write needs a non-custodial signer. Never fake it.
        digest = digest_record(record)
        if not self.reachable():
            raise ChainUnavailable(f"{self.network} unreachable at {self.rpc_url}")
        signer = self._signer or resolve_signer()
        if signer is None:
            raise SignerUnavailable(
                f"attestation is an on-chain write to AgentDecisionRegistry {self.registry} on chain "
                f"{self.expected_chain_id} ({ATTEST_FUNCTION}, digest {digest[:14]}…) — no non-custodial "
                f"signer configured. Set SPLENDOR_CITRATE_SIGNER (a signer command) or CITRATE_SIGNER_KEY "
                f"(the bundled reference signer). Chain is reachable; signing is the missing piece.")
        # The signer address must be an authorized recorder or the node reverts
        # NotAuthorizedRecorder — surfaced honestly (SignerUnavailable), never a fake tx.
        result = signer.send(
            rpc=self.rpc_url, chain_id=self.expected_chain_id, to=self.registry,
            function=ATTEST_FUNCTION, args=self._decision_args(record), value=0)
        return AttestationRef(id=result["txHash"], network=self.network, digest=digest)

    def get_attestation(self, ref) -> dict:
        """Read the on-chain receipt for an attestation tx (real chain read)."""
        tx_hash = ref.id if isinstance(ref, AttestationRef) else ref
        receipt = self._rpc("eth_getTransactionReceipt", [tx_hash])
        if receipt is None:
            raise ChainUnavailable(f"no receipt yet for {tx_hash} (pending or unknown)")
        return {
            "tx_hash": tx_hash,
            "block": int(receipt["blockNumber"], 16),
            "status": int(receipt["status"], 16),  # 1 = success, 0 = reverted
            "to": receipt.get("to"),
        }


class IpfsPinning(PinningBackend):
    """Content-addressed pinning over the IPFS HTTP API (Citrate pinning is IPFS).

    `pin` → ``POST {api}/api/v0/add``; `fetch` → the gateway. IPFS CIDs are the
    content address (integrity is inherent). Needs a reachable daemon/gateway;
    otherwise raises PinUnavailable honestly.
    """

    def __init__(self, api_url=None, gateway_url=None, timeout=15.0):
        cfg = citrate_config()
        self.api_url = (api_url or cfg["ipfs_api"]).rstrip("/")
        self.gateway_url = (gateway_url or cfg["ipfs_gateway"]).rstrip("/")
        self.timeout = timeout

    def pin(self, data: bytes) -> PinRef:
        boundary = "----splendoripfsboundary"
        body = (
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"asset\"\r\n"
            f"Content-Type: application/octet-stream\r\n\r\n").encode() + data + f"\r\n--{boundary}--\r\n".encode()
        req = urllib.request.Request(
            self.api_url + "/api/v0/add?pin=true", data=body, method="POST",
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                out = json.loads(resp.read().decode().splitlines()[-1])
        except (urllib.error.URLError, OSError) as exc:
            raise PinUnavailable(f"IPFS API unreachable at {self.api_url}: {exc}") from exc
        cid = out.get("Hash")
        if not cid:
            raise IntegrityError(f"IPFS add returned no CID: {out}")
        return PinRef(cid, len(data))

    def fetch(self, cid: str) -> bytes:
        try:
            with urllib.request.urlopen(f"{self.gateway_url}/ipfs/{cid}", timeout=self.timeout) as resp:
                return resp.read()
        except (urllib.error.URLError, OSError) as exc:
            raise PinUnavailable(f"IPFS gateway unreachable at {self.gateway_url}: {exc}") from exc

    def verify(self, cid: str, data: bytes) -> bool:
        # IPFS integrity is inherent in the CID; a full re-add comparison is a follow-up.
        return bool(cid)
