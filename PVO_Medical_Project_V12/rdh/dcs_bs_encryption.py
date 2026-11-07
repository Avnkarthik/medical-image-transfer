import numpy as np
import struct

def encrypt_image_exact(img, key, block_size=4):
    np.random.seed(key)
    H, W = img.shape
    new_h = H - (H % block_size)
    new_w = W - (W % block_size)
    
    encrypted = img.copy()
    
    if new_h > 0 and new_w > 0:
        main_region = encrypted[:new_h, :new_w]
        blocks = []
        for r in range(0, new_h, block_size):
            for c in range(0, new_w, block_size):
                blocks.append(main_region[r:r+block_size, c:c+block_size].copy())
        
        perm_2d = np.random.permutation(len(blocks))
        idx = 0
        for r in range(0, new_h, block_size):
            for c in range(0, new_w, block_size):
                encrypted[r:r+block_size, c:c+block_size] = blocks[perm_2d[idx]]
                idx += 1
                
    mask = np.ones((H, W), dtype=bool)
    mask[:new_h, :new_w] = False
    remainder_pixels = encrypted[mask]
    
    if len(remainder_pixels) > 0:
        perm_1d = np.random.permutation(len(remainder_pixels))
        encrypted[mask] = remainder_pixels[perm_1d]
        
    return encrypted

def decrypt_image_exact(encrypted_img, key, block_size=4):
    np.random.seed(key)
    H, W = encrypted_img.shape
    new_h = H - (H % block_size)
    new_w = W - (W % block_size)
    
    if new_h > 0 and new_w > 0:
        num_blocks = (new_h // block_size) * (new_w // block_size)
        perm_2d = np.random.permutation(num_blocks)
    else:
        perm_2d = np.array([])
        
    mask = np.ones((H, W), dtype=bool)
    mask[:new_h, :new_w] = False
    num_remainder = np.sum(mask)
    if num_remainder > 0:
        perm_1d = np.random.permutation(num_remainder)
        
    decrypted = encrypted_img.copy()
    
    if num_remainder > 0:
        remainder_pixels = decrypted[mask]
        inv_perm_1d = np.argsort(perm_1d)
        decrypted[mask] = remainder_pixels[inv_perm_1d]
        
    if new_h > 0 and new_w > 0:
        main_region = decrypted[:new_h, :new_w]
        blocks = []
        for r in range(0, new_h, block_size):
            for c in range(0, new_w, block_size):
                blocks.append(main_region[r:r+block_size, c:c+block_size].copy())
                
        inv_perm_2d = np.argsort(perm_2d)
        idx = 0
        for r in range(0, new_h, block_size):
            for c in range(0, new_w, block_size):
                decrypted[r:r+block_size, c:c+block_size] = blocks[inv_perm_2d[idx]]
                idx += 1
                
    return decrypted

def encrypt_ehr_text(ehr_str, key, block_size=16):
    data = ehr_str.encode('utf-8')
    payload = struct.pack(">I", len(data)) + data
    pad_len = (block_size - (len(payload) % block_size)) % block_size
    payload += bytes([pad_len] * pad_len)
    
    blocks = [payload[i:i+block_size] for i in range(0, len(payload), block_size)]
    np.random.seed(key + 1)
    perm = np.random.permutation(len(blocks))
    
    return b''.join([blocks[p] for p in perm])

def decrypt_ehr_text(scrambled_bytes, key, block_size=16):
    blocks = [scrambled_bytes[i:i+block_size] for i in range(0, len(scrambled_bytes), block_size)]
    
    np.random.seed(key + 1)
    perm = np.random.permutation(len(blocks))
    inv_perm = np.argsort(perm)
    
    unscrambled = b''.join([blocks[p] for p in inv_perm])
    length = struct.unpack(">I", unscrambled[:4])[0]
    return unscrambled[4:4+length].decode('utf-8')
