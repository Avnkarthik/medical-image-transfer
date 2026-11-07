import numpy as np
from rdh.cpvo import stable_pvo_sort, compute_prediction_errors, calculate_cpvo_capacity, validate_block_shape, get_sorted_blocks

class CapacityExceededError(ValueError): pass

def embed_block(block, payload_bits, bit_idx):
    stego = [int(v) for v in block]
    sorted_vals, sigma = stable_pvo_sort(stego)
    pe_max, pe_min = compute_prediction_errors(sorted_vals)
    total_bits = len(payload_bits)

    if bit_idx < total_bits:
        if pe_max == 1:
            stego[sigma[-1]] += int(payload_bits[bit_idx]); bit_idx += 1
        elif pe_max > 1: stego[sigma[-1]] += 1

    if bit_idx < total_bits:
        if pe_min == -1:
            stego[sigma[0]] -= int(payload_bits[bit_idx]); bit_idx += 1
        elif pe_min < -1: stego[sigma[0]] -= 1

    return stego, bit_idx

def embed_cpvo(encrypted_image, payload_bits, block_shape=(2, 2)):
    bh, bw = validate_block_shape(block_shape)
    payload_list = [int(b) for b in payload_bits]
    
    cap = calculate_cpvo_capacity(encrypted_image, block_shape)
    if len(payload_list) > cap:
        raise CapacityExceededError(f"Exceeds encrypted cap {cap}")

    stego = encrypted_image.copy().astype(np.int32)
    bit_idx = 0
    total_bits = len(payload_list)
    
    coords = get_sorted_blocks(encrypted_image, block_shape)

    for (r, c) in coords:
        if bit_idx >= total_bits: break
        block = [int(v) for v in stego[r:r+bh, c:c+bw].flatten()]
        new_block, bit_idx = embed_block(block, payload_list, bit_idx)
        stego[r:r+bh, c:c+bw] = np.array(new_block, dtype=np.int32).reshape(bh, bw)

    return stego.astype(np.uint8)
