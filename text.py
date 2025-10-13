import os
import hashlib
from Crypto.Cipher import AES

# Function to generate a random 32-byte key


def generate_key():
    return os.urandom(32)
# Function to generate SHA-256 hash of the key


def generate_key_hash(key: bytes):
    return hashlib.sha256(key).hexdigest()
# Function to encrypt data using AES encryption


def encrypt_data(data: bytes, key: bytes):
    if len(key) != 32:
        raise ValueError("Key must be 32 bytes long")
    cipher = AES.new(key, AES.MODE_EAX)
    ciphertext, tag = cipher.encrypt_and_digest(data)
    return cipher.nonce + tag + ciphertext
# Function to combine key and encrypted data


def combine_key_and_data(key: bytes, encrypted_data: bytes):
    return key + encrypted_data


# Main execution
if __name__ == "__main__":
    text = input("Enter text to encrypt: ")
    secret_key = generate_key()
    encrypted_text_data = encrypt_data(text.encode('utf-8'), secret_key)
    full_data_to_embed = combine_key_and_data(secret_key, encrypted_text_data)
    key_hash_code = generate_key_hash(secret_key)

    with open("data_to_embed.bin", "wb") as f:
        f.write(full_data_to_embed)

    with open("hash_code.txt", "w") as f:
        f.write(key_hash_code)

    print("first step done")
    print(f"1. Data to be embedded has been saved to the 'data_to_embed.bin' file. ({len(full_data_to_embed)} bytes)")
    print("2. Verification Code has been saved to the 'hash_code.txt' file.")
    print("SHAREABLE CODE:", key_hash_code)
