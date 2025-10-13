import struct
import hashlib
from PIL import Image
from Crypto.Cipher import AES

INPUT_IMAGE = "input.png"

def _bits_to_bytes(bits):
    b = bytearray()
    cur = 0
    cnt = 0
    for bit in bits:
        cur = (cur << 1) | bit
        cnt += 1
        if cnt == 8:
            b.append(cur)
            cur = 0
            cnt = 0
    return bytes(b)

def generate_key_hash(key: bytes):
    return hashlib.sha256(key).hexdigest()

def decrypt_with_key(key: bytes, data: bytes):
    if len(key) != 32:
        raise ValueError("Key must be 32 bytes long")
    nonce = data[:12]
    tag = data[12:28]
    ciphertext = data[28:]
    cipher = AES.new(key, AES.MODE_EAX, nonce=nonce)
    plaintext = cipher.decrypt_and_verify(ciphertext, tag)
    return cipher.decrypt_and_verify(ciphertext, tag)

def extract_data_from_image(path: str):
    img = Image.open(path)
    if img.mode not in ('RGB', 'RGBA'):
        img = img.convert('RGB')
    pixels = list(img.getdata())

    bits = []
    for pix in pixels:
        r, g, b = pix[:3]
        bits.append(r & 1)
        bits.append(g & 1)
        bits.append(b & 1)

    header_bits = bits[:32]
    header_bytes = _bits_to_bytes(header_bits)
    length = struct.unpack('>I', header_bytes)[0]
    total_bits_needed = (length + 4) * 8

    if total_bits_needed > len(bits):
        raise ValueError("Image does not contain enough data")
    data_bits = bits[32:32 + length * 8]
    data = _bits_to_bytes(data_bits)
    return data

# Main execution
if __name__ == "__main__":
    try:
        recieved_hash_code = input("Enter the verification code: ")
        recovered_data = extract_data_from_image(INPUT_IMAGE)
        RECOVERED_KEY = recovered_data[:32]
        RECOVERED_ENCRYPTED_TEXT = recovered_data[32:]
        RECOVERED_KEY_HASH = generate_key_hash(RECOVERED_KEY)
        if RECOVERED_KEY_HASH.lower() == recieved_hash_code.lower():
            decrypted_text = decrypt_with_key(RECOVERED_KEY, RECOVERED_ENCRYPTED_TEXT)
            print("Decrypted text:", decrypted_text.decode('utf-8'))
        else:
            print("Error: Verification code does not match.")
    except exception as e:
        pass
