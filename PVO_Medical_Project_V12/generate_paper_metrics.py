import numpy as np
import os
import time
import json
from pathlib import Path
from PIL import Image
from skimage.metrics import structural_similarity as ssim
from skimage.metrics import peak_signal_noise_ratio as psnr
from tabulate import tabulate

from rdh.medical_payload_manager import MedicalPayloadManager

def generate_ehr(size_in_chars):
    return {
        "pid": "MED-2026",
        "study": "CT/MRI Performance Test",
        "did": "did:hosp:apollo:123",
        "data": "A" * size_in_chars
    }

def run_academic_evaluation():
    input_dir = Path("input_images")
    if not input_dir.exists() or not list(input_dir.glob("*.*")):
        print("[ERROR] No images found in 'input_images/' directory.")
        return

    manager = MedicalPayloadManager(dcs_key=9999, aes_key_hex=os.urandom(32).hex())
    payload_sizes = [100, 500, 1000]
    results = []
    
    print("Starting V12 (100-Layer Encrypted Payload Extractor) Evaluation...\n")
    
    for img_path in input_dir.iterdir():
        if not img_path.is_file(): continue
            
        try:
            with Image.open(img_path) as img:
                cover = np.asarray(img.convert("L"), dtype=np.uint8).copy()
        except Exception:
            continue
            
        H, W = cover.shape
        total_pixels = H * W
        
        for p_size in payload_sizes:
            ehr_data = generate_ehr(p_size)
            base_payload_bits = len(json.dumps(ehr_data).encode('utf-8')) * 8
            bpp = base_payload_bits / total_pixels
            
            try:
                start_embed = time.perf_counter()
                stego_image, tx_hash, layers, encrypted_lm = manager.process_and_embed(cover, ehr_data)
                embed_time_ms = (time.perf_counter() - start_embed) * 1000
                
                current_psnr = psnr(cover, stego_image, data_range=255)
                
                start_extract = time.perf_counter()
                recovered_ehr, decrypted_image, is_auth = manager.extract_and_decrypt(stego_image, encrypted_lm)
                extract_time_ms = (time.perf_counter() - start_extract) * 1000
                
                is_exact = np.array_equal(cover, decrypted_image)
                
                results.append([
                    img_path.name[:15] + "...", 
                    f"{cover.shape[0]}x{cover.shape[1]}",
                    base_payload_bits, 
                    len(encrypted_lm),
                    layers,
                    f"{current_psnr:.2f}",
                    f"{embed_time_ms:.1f}",
                    f"{extract_time_ms:.1f}",
                    "Yes" if is_exact and is_auth else "No"
                ])
                
            except Exception as e:
                results.append([
                    img_path.name[:15] + "...", f"{cover.shape[0]}x{cover.shape[1]}", base_payload_bits, "FAIL",
                    "FAIL", "N/A", "N/A", "N/A", str(e)[:15]
                ])

    headers = [
        "Image Name", "Resolution", "Payload\n(Bits)", "Blockchain\nLM (Bytes)", 
        "Layers\nUsed", "Encrypted\nPSNR (dB)", 
        "Embed\nTime (ms)", "Extract\nTime (ms)", "100% Exact\nRecovery"
    ]
    
    print(tabulate(results, headers=headers, tablefmt="grid"))

if __name__ == "__main__":
    run_academic_evaluation()
