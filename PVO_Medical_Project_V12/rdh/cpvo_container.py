import struct
import zlib
import numpy as np
from typing import Iterable, List, Tuple
from rdh.embed import embed_cpvo, CapacityExceededError
from rdh.extract import extract_cpvo
from rdh.cpvo import calculate_cpvo_capacity

MAGIC = b"CPVO"
VERSION = 1

_HEADER_PREFIX = struct.Struct(">4sBBBBII")
_HEADER_SIZE = _HEADER_PREFIX.size + 4
HEADER_BITS = _HEADER_SIZE * 8

class ContainerError(ValueError): pass

def _bits_to_bytes(bits):
    values = [int(bit) for bit in bits]
    packed = bytearray((len(values) + 7) // 8)
    for i, bit in enumerate(values):
        if bit: packed[i // 8] |= 1 << (7 - (i % 8))
    return bytes(packed)

def _bytes_to_bits(data):
    return [(byte >> shift) & 1 for byte in data for shift in range(7, -1, -1)]

def _payload_crc(payload_bits):
    return zlib.crc32(_bits_to_bytes(payload_bits)) & 0xFFFFFFFF

def _encode_header(payload_bits, block_h, block_w, flags):
    prefix = _HEADER_PREFIX.pack(
        MAGIC, VERSION, block_h, block_w, flags,
        len(payload_bits), _payload_crc(payload_bits)
    )
    return prefix + struct.pack(">I", zlib.crc32(prefix) & 0xFFFFFFFF)

def embed_encrypted_multi_layer(encrypted_image: np.ndarray, payload_bits: Iterable[int], max_layers=100) -> Tuple[np.ndarray, int]:
    current_image = encrypted_image.copy()
    remaining_bits = list(payload_bits)
    layers_used = 0
    shapes_to_try = [(2,2), (1,3), (1,4), (2,3)]
    
    while remaining_bits:
        if layers_used >= max_layers:
            raise CapacityExceededError(f"Exceeded max layers ({max_layers}).")
            
        best_shape = None
        best_usable = -999999
        
        for shape in shapes_to_try:
            raw_cap = calculate_cpvo_capacity(current_image, shape)
            usable = raw_cap - HEADER_BITS
            if usable > best_usable:
                best_usable = usable
                best_shape = shape
                
        if best_usable <= 0:
            raise CapacityExceededError(f"Capacity exhausted at layer {layers_used+1}.")
            
        chunk = remaining_bits[:best_usable]
        remaining_bits = remaining_bits[best_usable:]
        flags = 0 if layers_used == 0 else 1
        
        header = _encode_header(chunk, best_shape[0], best_shape[1], flags)
        stream = _bytes_to_bits(header) + chunk
        current_image = embed_cpvo(current_image, stream, block_shape=best_shape)
        layers_used += 1
        
    return current_image, layers_used

def extract_encrypted_multi_layer(stego_image: np.ndarray) -> Tuple[List[int], np.ndarray]:
    current_image = stego_image.copy()
    full_payload = []
    shapes_to_try = [(2,2), (1,3), (1,4), (2,3)]
    
    while True:
        valid_shape = None
        header_info = None
        
        for shape in shapes_to_try:
            try:
                _ignore1, header_bits = extract_cpvo(current_image.copy(), HEADER_BITS, block_shape=shape)
                header_bytes = _bits_to_bytes(header_bits)
                prefix, crc_bytes = header_bytes[:-4], header_bytes[-4:]
                
                (magic, version, bh, bw, flags, payload_bits_len, payload_crc) = _HEADER_PREFIX.unpack(prefix)
                if magic == MAGIC and bh == shape[0] and bw == shape[1]:
                    valid_shape = shape
                    header_info = (flags, payload_bits_len, payload_crc)
                    break
            except Exception:
                continue
                
        if not valid_shape:
            raise ContainerError("Invalid Magic. Image is corrupted or not CPVO.")
            
        flags, payload_bits_len, payload_crc = header_info
        total_bits = HEADER_BITS + payload_bits_len
        
        recovered_image, stream_bits = extract_cpvo(current_image.copy(), total_bits, block_shape=valid_shape)
        
        payload_chunk = stream_bits[HEADER_BITS : total_bits]
        if _payload_crc(payload_chunk) != payload_crc:
            raise ContainerError("Payload CRC mismatch in layer.")
            
        full_payload = payload_chunk + full_payload
        current_image = recovered_image
        
        if flags == 0:
            break
            
    return full_payload, current_image
