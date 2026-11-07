import json, os, lzma
from rdh.cpvo_container import embed_encrypted_multi_layer, extract_encrypted_multi_layer, _bits_to_bytes, _bytes_to_bits
from rdh.dcs_bs_encryption import encrypt_image_exact, decrypt_image_exact, encrypt_ehr_text, decrypt_ehr_text
from rdh.cpvo import preprocess_boundaries, restore_boundaries
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import numpy as np
import imagehash
from PIL import Image

class MedicalPayloadManager:
    def __init__(self, dcs_key: int, aes_key_hex: str):
        self.dcs_key = dcs_key
        self.aesgcm = AESGCM(bytes.fromhex(aes_key_hex))

    def process_and_embed(self, original_image: np.ndarray, ehr_data: dict) -> tuple[np.ndarray, str, int, bytes]:
        img_pre, lm = preprocess_boundaries(original_image)
        compressed_lm = lzma.compress(np.packbits(lm.flatten()), preset=9 | lzma.PRESET_EXTREME)
        nonce = os.urandom(12)
        encrypted_lm = nonce + self.aesgcm.encrypt(nonce, compressed_lm, associated_data=b"BLOCKCHAIN_LM")
        
        encrypted_img = encrypt_image_exact(img_pre, key=self.dcs_key, block_size=4)
        
        pil_img = Image.fromarray(original_image)
        h_hash = str(imagehash.phash(pil_img))
        ehr_data['img_hash'] = h_hash
        ehr_json = json.dumps(ehr_data)
        
        scrambled_ehr_bytes = encrypt_ehr_text(ehr_json, key=self.dcs_key)
        payload_bits = _bytes_to_bits(scrambled_ehr_bytes)
        
        ewm_stego, layers_used = embed_encrypted_multi_layer(encrypted_img, payload_bits, max_layers=100)
        
        return ewm_stego, h_hash, layers_used, encrypted_lm

    def extract_and_decrypt(self, ewm_stego: np.ndarray, encrypted_lm: bytes) -> tuple[dict, np.ndarray, bool]:
        payload_bits, recovered_encrypted = extract_encrypted_multi_layer(ewm_stego)
        scrambled_ehr_bytes = _bits_to_bytes(payload_bits)
        
        ehr_json = decrypt_ehr_text(scrambled_ehr_bytes, key=self.dcs_key)
        ehr_data = json.loads(ehr_json)
        
        decrypted_pre = decrypt_image_exact(recovered_encrypted, key=self.dcs_key, block_size=4)
        
        nonce, ciphertext = encrypted_lm[:12], encrypted_lm[12:]
        compressed_lm = self.aesgcm.decrypt(nonce, ciphertext, associated_data=b"BLOCKCHAIN_LM")
        lm_packed = lzma.decompress(compressed_lm)
        
        lm_flat = np.unpackbits(np.frombuffer(lm_packed, dtype=np.uint8))[:decrypted_pre.size]
        lm = lm_flat.reshape(decrypted_pre.shape).astype(bool)
        
        restored_original = restore_boundaries(decrypted_pre, lm)
        
        pil_img = Image.fromarray(restored_original)
        actual_hash = str(imagehash.phash(pil_img))
        is_authentic = (actual_hash == ehr_data.get('img_hash'))
        
        return ehr_data, restored_original, is_authentic
