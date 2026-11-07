import numpy as np

def validate_block_shape(block_shape):
    if not isinstance(block_shape, (tuple, list)) or len(block_shape) != 2:
        raise ValueError(f"Block shape must be a tuple, got {block_shape}")
    bh, bw = block_shape
    if bh < 1 or bw < 1: raise ValueError("Positive integers required")
    if bh * bw < 3: raise ValueError("Block size n >= 3 required")
    return bh, bw

def stable_pvo_sort(block):
    indexed = [(int(val), i) for i, val in enumerate(block)]
    indexed_sorted = sorted(indexed, key=lambda x: (x[0], x[1]))
    return [x[0] for x in indexed_sorted], [x[1] for x in indexed_sorted]

def compute_prediction_errors(sorted_vals):
    pe_max = int(sorted_vals[-1]) - int(sorted_vals[-2])
    pe_min = int(sorted_vals[0]) - int(sorted_vals[1])
    return pe_max, pe_min

def preprocess_boundaries(image):
    lm = (image == 0) | (image == 255)
    img_pre = image.astype(np.int32)
    img_pre[image == 0] = 1
    img_pre[image == 255] = 254
    return img_pre.astype(np.uint8), lm

def restore_boundaries(recovered_pre, lm):
    recovered_orig = recovered_pre.copy()
    recovered_orig[lm & (recovered_pre == 1)] = 0
    recovered_orig[lm & (recovered_pre == 254)] = 255
    return recovered_orig.astype(np.uint8)

def get_sorted_blocks(img, block_shape=(2, 2)):
    bh, bw = validate_block_shape(block_shape)
    H, W = img.shape
    blocks = []
    
    for r in range(0, H - bh + 1, bh):
        for c in range(0, W - bw + 1, bw):
            block = img[r:r+bh, c:c+bw].flatten()
            s, _ = stable_pvo_sort(block)
            noise_level = int(s[-2]) - int(s[1])
            blocks.append((noise_level, r, c))
            
    blocks.sort(key=lambda x: (x[0], x[1], x[2]))
    return [(r, c) for nl, r, c in blocks]

def calculate_cpvo_capacity(img, block_shape=(2, 2)):
    coords = get_sorted_blocks(img, block_shape)
    capacity = 0
    bh, bw = block_shape
    for (r, c) in coords:
        block = [int(v) for v in img[r:r+bh, c:c+bw].flatten()]
        s, _ = stable_pvo_sort(block)
        pe_max, pe_min = compute_prediction_errors(s)
        if pe_max == 1: capacity += 1
        if pe_min == -1: capacity += 1
    return capacity
