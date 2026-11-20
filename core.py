"""StegoCrypt core: password-based AES encryption + LSB image steganography.

No GUI code here, so everything in this module can be tested on its own.

Payload format (v2), embedded in the least-significant bits of the R,G,B
channels, starting at the first pixel:

    [4 bytes  big-endian payload length]
    [4 bytes  magic  b"SGC2"]
    [4 bytes  big-endian PBKDF2 iteration count]
    [16 bytes salt][16 bytes nonce][16 bytes tag][ciphertext]

Images written by the first version of this tool (no magic, 200 000 PBKDF2
iterations) can still be read.
"""
from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from PIL import Image

MAGIC = b"SGC2"
ITERATIONS = 600_000          # PBKDF2-HMAC-SHA256 (OWASP 2023 recommendation)
LEGACY_ITERATIONS = 200_000
MAX_ITERATIONS = 10_000_000   # refuse absurd values from a crafted image
HEADER_BITS = 32
MIN_PASSWORD_LEN = 8


class StegoError(Exception):
    """Raised with a message that is safe to show to the user."""


# ---------------------------------------------------------------- crypto ---

def _derive_key(password: str, salt: bytes, iterations: int) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations, dklen=32)


def encrypt(password: str, data: bytes, iterations: int = ITERATIONS) -> bytes:
    salt = get_random_bytes(16)
    cipher = AES.new(_derive_key(password, salt, iterations), AES.MODE_EAX)
    ciphertext, tag = cipher.encrypt_and_digest(data)
    return MAGIC + struct.pack(">I", iterations) + salt + cipher.nonce + tag + ciphertext


def decrypt(password: str, blob: bytes) -> bytes:
    if blob[:4] == MAGIC:
        if len(blob) < 56:
            raise StegoError("The hidden data is truncated.")
        iterations = struct.unpack(">I", blob[4:8])[0]
        if not 1 <= iterations <= MAX_ITERATIONS:
            raise StegoError("This image does not contain valid StegoCrypt data.")
        body = blob[8:]
    else:  # legacy v1
        iterations, body = LEGACY_ITERATIONS, blob
        if len(body) < 48:
            raise StegoError("This image does not contain StegoCrypt data.")
    salt, nonce, tag, ciphertext = body[:16], body[16:32], body[32:48], body[48:]
    cipher = AES.new(_derive_key(password, salt, iterations), AES.MODE_EAX, nonce=nonce)
    try:
        return cipher.decrypt_and_verify(ciphertext, tag)
    except ValueError:
        raise StegoError("Wrong password, or the image was modified (e.g. re-saved as JPEG).") from None


# ---------------------------------------------------------------- stego ----

@dataclass
class _Pixels:
    raw: bytearray
    mode: str
    size: tuple
    step: int  # bytes per pixel in raw (3 for RGB, 4 for RGBA)


def _load(path: str) -> _Pixels:
    try:
        img = Image.open(path)
        img.load()
    except Exception as e:
        raise StegoError(f"Cannot open the image: {e}") from None
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    return _Pixels(bytearray(img.tobytes()), img.mode, img.size, 3 if img.mode == "RGB" else 4)


def _index(bit: int, step: int) -> int:
    """Position in the raw pixel bytes of the n-th carrier bit (alpha is skipped)."""
    return (bit // 3) * step + (bit % 3)


def capacity_bytes(path: str) -> int:
    """How many payload bytes fit into the image (header excluded)."""
    with Image.open(path) as img:
        w, h = img.size
    return max(0, (w * h * 3 - HEADER_BITS) // 8)


def embed(image_path: str, payload: bytes, output_path: str) -> None:
    px = _load(image_path)
    cap = (px.size[0] * px.size[1] * 3 - HEADER_BITS) // 8
    if len(payload) > cap:
        raise StegoError(f"The image is too small: {len(payload)} bytes needed, {cap} available.")
    data = struct.pack(">I", len(payload)) + payload
    bit = 0
    for byte in data:
        for shift in range(7, -1, -1):
            i = _index(bit, px.step)
            px.raw[i] = (px.raw[i] & 0xFE) | ((byte >> shift) & 1)
            bit += 1
    out = Image.frombytes(px.mode, px.size, bytes(px.raw))
    out.save(output_path, format="PNG")


def extract(image_path: str) -> bytes:
    px = _load(image_path)
    carrier_bits = px.size[0] * px.size[1] * 3

    def read_bytes(first_bit: int, count: int) -> bytes:
        out = bytearray(count)
        for n in range(count):
            v = 0
            for k in range(8):
                v = (v << 1) | (px.raw[_index(first_bit + n * 8 + k, px.step)] & 1)
            out[n] = v
        return bytes(out)

    if carrier_bits < HEADER_BITS:
        raise StegoError("The image is too small to contain hidden data.")
    length = struct.unpack(">I", read_bytes(0, 4))[0]
    if length < 48 or HEADER_BITS + length * 8 > carrier_bits:
        raise StegoError("No hidden data found in this image (or it is not a lossless PNG).")
    return read_bytes(HEADER_BITS, length)


# ------------------------------------------------------------ convenience --

def encrypt_into_image(image_path: str, text: str, password: str, output_path: str) -> int:
    """Encrypt `text` and hide it in `image_path`, writing a PNG. Returns bytes embedded."""
    if len(password) < MIN_PASSWORD_LEN:
        raise StegoError(f"The password must be at least {MIN_PASSWORD_LEN} characters.")
    if not text:
        raise StegoError("There is no text to hide.")
    blob = encrypt(password, text.encode("utf-8"))
    embed(image_path, blob, output_path)
    return len(blob)


def decrypt_from_image(image_path: str, password: str) -> str:
    plain = decrypt(password, extract(image_path))
    try:
        return plain.decode("utf-8")
    except UnicodeDecodeError:
        raise StegoError("Decrypted, but the content is not valid UTF-8 text.") from None
