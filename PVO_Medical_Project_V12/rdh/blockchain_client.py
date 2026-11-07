import asyncio
import base64
import json
import os
from pathlib import Path

cwd = Path(os.getcwd())
WORKSPACE_ROOT = cwd.parent if cwd.name == "PVO_Medical_Project_V12" else cwd

NETWORK_DIR = WORKSPACE_ROOT / "fabric-samples" / "test-network"
BIN_DIR = WORKSPACE_ROOT / "fabric-samples" / "bin"

# TLS Certificates for Both Organizations (Required for Endorsement)
ORG1_TLS_ROOTCERT = str(NETWORK_DIR / "organizations/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt")
ORG2_TLS_ROOTCERT = str(NETWORK_DIR / "organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt")
ORDERER_CA = str(NETWORK_DIR / "organizations/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem")

# Secure Environment Variables for Org1 (Hospital A)
ORG1_ENV = os.environ.copy()
ORG1_ENV["FABRIC_CFG_PATH"] = str(WORKSPACE_ROOT / "fabric-samples" / "config")
ORG1_ENV["CORE_PEER_TLS_ENABLED"] = "true"
ORG1_ENV["CORE_PEER_LOCALMSPID"] = "Org1MSP"
ORG1_ENV["CORE_PEER_TLS_ROOTCERT_FILE"] = ORG1_TLS_ROOTCERT
ORG1_ENV["CORE_PEER_MSPCONFIGPATH"] = str(NETWORK_DIR / "organizations/peerOrganizations/org1.example.com/users/User1@org1.example.com/msp")
ORG1_ENV["CORE_PEER_ADDRESS"] = "localhost:7051"

class FabricRDHClient:
    def __init__(self):
        self.channel_name = "medicalchannel"
        self.chaincode_name = "rdh_cc"
        self.peer_bin = str(BIN_DIR / "peer")

    async def submit_lm(self, tx_hash: str, encrypted_lm_bytes: bytes):
        """Hospital A: Commits the Location Map with MULTI-ORG ENDORSEMENT."""
        lm_b64 = base64.b64encode(encrypted_lm_bytes).decode('utf-8')
        timestamp = "2026-11-07T13:02:00Z"
        
        args = json.dumps({"function": "CreateRecord", "Args": [tx_hash, lm_b64, timestamp]})
        
        # We must ping BOTH peers to satisfy the Fabric Endorsement Policy
        cmd = [
            self.peer_bin, "chaincode", "invoke",
            "-o", "localhost:7050",
            "--ordererTLSHostnameOverride", "orderer.example.com",
            "--tls", "--cafile", ORDERER_CA,
            "-C", self.channel_name,
            "-n", self.chaincode_name,
            "--peerAddresses", "localhost:7051",
            "--tlsRootCertFiles", ORG1_TLS_ROOTCERT,
            "--peerAddresses", "localhost:9051",  # <-- Added Org2 Peer
            "--tlsRootCertFiles", ORG2_TLS_ROOTCERT, # <-- Added Org2 Cert
            "-c", args
        ]
        
        print(f"[BLOCKCHAIN] Submitting Encrypted LM for Hash: {tx_hash[:10]}...")
        proc = await asyncio.create_subprocess_exec(
            *cmd, env=ORG1_ENV, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            raise Exception(f"Blockchain submission failed: {stderr.decode()}")
        print("[BLOCKCHAIN] Endorsed by Org1 & Org2. Successfully committed to Ledger.")

    async def fetch_lm(self, tx_hash: str) -> bytes:
        """Hospital B: Queries the Ledger for the Location Map."""
        args = json.dumps({"function": "ReadRecord", "Args": [tx_hash]})
        
        # Queries only need to hit the local peer (Org1)
        cmd = [
            self.peer_bin, "chaincode", "query",
            "-C", self.channel_name,
            "-n", self.chaincode_name,
            "-c", args
        ]
        
        print(f"[BLOCKCHAIN] Fetching LM for Hash: {tx_hash[:10]}...")
        proc = await asyncio.create_subprocess_exec(
            *cmd, env=ORG1_ENV, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            raise Exception(f"Blockchain query failed: {stderr.decode()}")
            
        result_json = json.loads(stdout.decode().strip())
        print("[BLOCKCHAIN] Record retrieved successfully.")
        
        return base64.b64decode(result_json["encrypted_lm"])