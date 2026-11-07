import asyncio
import os
import numpy as np
from pathlib import Path
from PIL import Image
from rdh.medical_payload_manager import MedicalPayloadManager
from rdh.blockchain_client import FabricRDHClient

async def main():
    manager = MedicalPayloadManager(dcs_key=9999, aes_key_hex=os.urandom(32).hex())
    blockchain = FabricRDHClient()
    
    # Ensure there is an image to test
    images = list(Path("input_images").glob("*.*"))
    if not images:
        print("ERROR: Please place a medical image inside the input_images/ folder first!")
        return
        
    img_path = images[0]
    cover = np.asarray(Image.open(img_path).convert("L"), dtype=np.uint8).copy()
    ehr_data = {"pid": "MED-2026", "study": "Blockchain Test", "notes": "Full Integration"}
    
    print("\n--- HOSPITAL A (SENDER) ---")
    stego_image, tx_hash, layers, encrypted_lm = manager.process_and_embed(cover, ehr_data)
    print(f"1. Image Encrypted & EHR Embedded ({layers} layers used).")
    
    await blockchain.submit_lm(tx_hash, encrypted_lm)
    
    print("\n--- WAITING FOR BLOCKCHAIN CONSENSUS ---")
    print("Allowing Fabric peers 3 seconds to order and commit the transaction block...")
    await asyncio.sleep(3)
    
    print("\n--- HOSPITAL B (RECEIVER) ---")
    retrieved_lm = await blockchain.fetch_lm(tx_hash)
    
    recovered_ehr, decrypted_image, is_auth = manager.extract_and_decrypt(stego_image, retrieved_lm)
    print("4. Extraction, Decryption, and Boundary Restoration Complete.")
    
    is_exact = np.array_equal(cover, decrypted_image)
    print(f"5. Final Integrity Check: Exact Mathematical Match? -> {is_exact}")
    print(f"6. Phash Authenticated? -> {is_auth}\n")

if __name__ == "__main__":
    asyncio.run(main())