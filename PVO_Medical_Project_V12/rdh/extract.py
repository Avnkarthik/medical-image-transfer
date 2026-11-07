import numpy as np
from rdh.cpvo import stable_pvo_sort, compute_prediction_errors, validate_block_shape, get_sorted_blocks

def extract_block(stego_block, extracted_bits, target_bits):
    recovered = [int(v) for v in stego_block]
    sorted_vals, sigma = stable_pvo_sort(recovered)
    pe_max_prime, pe_min_prime = compute_prediction_errors(sorted_vals)

    if len(extracted_bits) < target_bits:
        if pe_max_prime == 1: extracted_bits.append(0)
        elif pe_max_prime == 2:
            extracted_bits.append(1); recovered[sigma[-1]] -= 1
        elif pe_max_prime > 2: recovered[sigma[-1]] -= 1

    if len(extracted_bits) < target_bits:
        if pe_min_prime == -1: extracted_bits.append(0)
        elif pe_min_prime == -2:
            extracted_bits.append(1); recovered[sigma[0]] += 1
        elif pe_min_prime < -2: recovered[sigma[0]] += 1

    return recovered, extracted_bits

def extract_cpvo(stego_image, num_bits, block_shape=(2, 2)):
    bh, bw = validate_block_shape(block_shape)
    recovered = stego_image.astype(np.int32)
    extracted_bits = []
    
    coords = get_sorted_blocks(stego_image, block_shape)

    for (r, c) in coords:
        if len(extracted_bits) >= num_bits: break
        block = [int(v) for v in recovered[r:r+bh, c:c+bw].flatten()]
        new_block, extracted_bits = extract_block(block, extracted_bits, num_bits)
        recovered[r:r+bh, c:c+bw] = np.array(new_block, dtype=np.int32).reshape(bh, bw)

    return recovered.astype(np.uint8), extracted_bits
