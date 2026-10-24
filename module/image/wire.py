"""Bounded, non-executable array transport shared by image and OCR RPC."""
from __future__ import annotations

import struct

import numpy as np


IMAGE_PROTOCOL = "oas-image-v1"
MAX_IMAGE_DIMENSION = 8192
MAX_IMAGE_BYTES = 64 * 1024 * 1024
_MAGIC = b"OASIMG1\0"
_HEADER = struct.Struct("!8sBBBBII")
_DTYPES = tuple(np.dtype(value) for value in (
    "u1", "i1", "<u2", "<i2", "<u4", "<i4", "<f4", "<f8", "?",
))


def _validate_shape(height: int, width: int, ndim: int, channels: int, dtype: np.dtype) -> int:
    if not (0 < height <= MAX_IMAGE_DIMENSION and 0 < width <= MAX_IMAGE_DIMENSION):
        raise ValueError("Image dimensions must be between 1 and 8192")
    if ndim not in (2, 3) or (ndim == 2 and channels != 1) or channels not in (1, 3, 4):
        raise ValueError("Image must be a 2D array or have 1, 3 or 4 channels")
    size = height * width * channels * dtype.itemsize
    if size > MAX_IMAGE_BYTES:
        raise ValueError("Image payload exceeds 64 MiB")
    return size


def encode_image(image: np.ndarray) -> bytes:
    """Encode numeric pixels without pickle, preserving dtype, shape and values."""
    if not isinstance(image, np.ndarray):
        raise TypeError("Image payload must be numpy.ndarray")
    if image.ndim not in (2, 3):
        raise ValueError("Image must have two or three dimensions")
    dtype = image.dtype.newbyteorder("<")
    if dtype not in _DTYPES:
        raise ValueError(f"Unsupported image dtype: {image.dtype}")
    height, width = image.shape[:2]
    channels = image.shape[2] if image.ndim == 3 else 1
    _validate_shape(height, width, image.ndim, channels, dtype)
    pixels = np.asarray(image, dtype=dtype, order="C").tobytes()
    return _HEADER.pack(_MAGIC, _DTYPES.index(dtype), image.ndim, channels, 0, height, width) + pixels


def decode_image(payload: bytes) -> np.ndarray:
    """Validate the complete packet before allocating an owned pixel array."""
    if not isinstance(payload, bytes):
        raise TypeError("Image RPC payload must be bytes")
    if len(payload) < _HEADER.size or len(payload) > MAX_IMAGE_BYTES + _HEADER.size:
        raise ValueError("Invalid image payload length")
    magic, dtype_code, ndim, channels, flags, height, width = _HEADER.unpack_from(payload)
    if magic != _MAGIC:
        raise ValueError("Unsupported image protocol; restart image/OCR services and clients after updating")
    if flags or dtype_code >= len(_DTYPES):
        raise ValueError("Invalid image payload header")
    dtype = _DTYPES[dtype_code]
    size = _validate_shape(height, width, ndim, channels, dtype)
    if len(payload) != _HEADER.size + size:
        raise ValueError("Image payload length does not match its dimensions")
    shape = (height, width) if ndim == 2 else (height, width, channels)
    return np.frombuffer(payload, dtype=dtype, offset=_HEADER.size).reshape(shape).copy()
