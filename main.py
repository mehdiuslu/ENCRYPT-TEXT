import os
import struct
import hashlib
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes


def derive_key_from_password(password: str, salt: bytes, iterations: int = 200_000) -> bytes:
    return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations, dklen=32)

def encrypt_with_password(password: str, data: bytes) -> bytes:
    salt = get_random_bytes(16)
    key = derive_key_from_password(password, salt)
    cipher = AES.new(key, AES.MODE_EAX)
    ciphertext, tag = cipher.encrypt_and_digest(data)
    return salt + cipher.nonce + tag + ciphertext

def decrypt_with_password(password: str, blob: bytes) -> bytes:
    if len(blob) < 48:
        raise ValueError("Invalid encrypted data format.")
    salt = blob[:16]
    nonce = blob[16:32]
    tag = blob[32:48]
    ciphertext = blob[48:]
    key = derive_key_from_password(password, salt)
    cipher = AES.new(key, AES.MODE_EAX, nonce=nonce)
    plaintext = cipher.decrypt_and_verify(ciphertext, tag)
    return plaintext


def _bytes_to_bits(data: bytes):
    for byte in data:
        for i in range(7, -1, -1):
            yield (byte >> i) & 1

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

def embed_data_in_image(image_path: str, data: bytes, output_path: str):
    img = Image.open(image_path)
    if img.mode not in ('RGB', 'RGBA'):
        img = img.convert('RGB')
    pixels = list(img.getdata())
    length = len(data)
    header = struct.pack('>I', length)
    full = header + data
    bits = list(_bytes_to_bits(full))
    capacity = len(pixels) * 3
    if len(bits) > capacity:
        raise ValueError(f"Not enough capacity. Required bits: {len(bits)}, Capacity: {capacity}")
    out_pixels = []
    bit_idx = 0
    for pix in pixels:
        r, g, b = pix[:3]
        new_rgb = []
        for channel in (r, g, b):
            if bit_idx < len(bits):
                channel = (channel & ~1) | bits[bit_idx]
                bit_idx += 1
            new_rgb.append(channel)
        if len(pix) == 4:
            out_pixels.append(tuple(new_rgb + [pix[3]]))
        else:
            out_pixels.append(tuple(new_rgb))
    img_out = Image.new(img.mode, img.size)
    img_out.putdata(out_pixels)
    img_out.save(output_path)

def extract_data_from_image(image_path: str) -> bytes:
    img = Image.open(image_path)
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
        raise ValueError("Image does not contain enough data or is corrupted.")
    data_bits = bits[32:32 + length * 8]
    data = _bits_to_bytes(data_bits)
    return data

def max_embed_bytes_for_image(path):
    img = Image.open(path)
    if img.mode not in ('RGB', 'RGBA'):
        img = img.convert('RGB')
    w, h = img.size
    capacity_bits = w * h * 3
    max_bytes = (capacity_bits - 32) // 8
    return max_bytes


class StegoApp:
    def __init__(self, root):
        self.root = root
        root.title("StegoCrypt - Image Encryption & Hiding Tool")
        self.input_path = None
        self.output_path = None

        top = tk.Frame(root, bg="#2c3e50")
        top.pack(padx=10, pady=10, fill="x")

        tk.Button(top, text="🔒 Embed Data", command=self.open_embed_window, bg="#27ae60", fg="white", font=("Arial", 10, "bold")).pack(side="left", padx=8)
        tk.Button(top, text="🔓 Extract Data", command=self.open_extract_window, bg="#2980b9", fg="white", font=("Arial", 10, "bold")).pack(side="left", padx=8)

        label = tk.Label(root, text="Welcome to StegoCrypt", font=("Arial", 14, "bold"))
        label.pack(pady=10)
        tk.Label(root, text="Hide encrypted messages inside PNG images securely.", font=("Arial", 10)).pack()

    def open_embed_window(self):
        win = tk.Toplevel(self.root)
        win.title("Embed Encrypted Text into Image")
        win.geometry("700x600")

        frame = tk.Frame(win)
        frame.pack(fill="both", expand=True, padx=8, pady=8)

        img_sel_frame = tk.Frame(frame)
        img_sel_frame.pack(fill="x", pady=4)
        tk.Button(img_sel_frame, text="Select Source Image", command=lambda: self.select_input_image_for_embed(win)).pack(side="left")
        self.embed_capacity_label = tk.Label(img_sel_frame, text="(No image selected yet)")
        self.embed_capacity_label.pack(side="left", padx=8)

        self.preview_label_emb = tk.Label(frame, text="No image preview", width=60, height=12, bd=1, relief="sunken")
        self.preview_label_emb.pack(pady=6)

        tk.Label(frame, text="Text to hide:").pack(anchor="w")
        self.text_box = tk.Text(frame, height=8)
        self.text_box.pack(fill="x", pady=(0,8))

        pw_frame = tk.Frame(frame)
        pw_frame.pack(fill="x", pady=4)
        tk.Label(pw_frame, text="Password (to share with recipient):").pack(side="left")
        self.password_entry = tk.Entry(pw_frame, show="*")
        self.password_entry.pack(side="left", padx=6)

        out_frame = tk.Frame(frame)
        out_frame.pack(fill="x", pady=4)
        tk.Button(out_frame, text="Select Output File", command=lambda: self.select_output_path(win)).pack(side="left")
        self.output_path_label = tk.Label(out_frame, text="(No output selected)")
        self.output_path_label.pack(side="left", padx=8)

        tk.Button(frame, text="Encrypt & Embed", bg="#2ecc71", fg="white", command=self.action_encrypt_and_embed).pack(pady=8)

    def select_input_image_for_embed(self, window):
        path = filedialog.askopenfilename(title="Select Image", filetypes=[("PNG", "*.png")])
        if not path:
            return
        self.input_path = path
        max_bytes = max_embed_bytes_for_image(path)
        self.embed_capacity_label.config(text=f"Max embed capacity: {max_bytes} bytes")
        img = Image.open(path)
        img.thumbnail((500, 350))
        self.embed_tkimg = ImageTk.PhotoImage(img)
        self.preview_label_emb.config(image=self.embed_tkimg, text="")

    def select_output_path(self, window):
        path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png")], title="Save as")
        if not path:
            return
        self.output_path = path
        self.output_path_label.config(text=path)

    def action_encrypt_and_embed(self):
        if not self.input_path:
            messagebox.showerror("Error", "Select a source image first.")
            return
        if not self.output_path:
            messagebox.showerror("Error", "Select an output file first.")
            return
        text = self.text_box.get("1.0", "end").strip()
        if not text:
            messagebox.showerror("Error", "Text cannot be empty.")
            return
        password = self.password_entry.get().strip()
        if not password or len(password) < 6:
            messagebox.showerror("Error", "Password must be at least 6 characters.")
            return
        try:
            encrypted_blob = encrypt_with_password(password, text.encode('utf-8'))
        except Exception as e:
            messagebox.showerror("Encryption Error", str(e))
            return
        max_bytes = max_embed_bytes_for_image(self.input_path)
        if len(encrypted_blob) > max_bytes:
            messagebox.showerror("Error", f"Image too small. Required: {len(encrypted_blob)}, Capacity: {max_bytes}")
            return
        try:
            embed_data_in_image(self.input_path, encrypted_blob, self.output_path)
        except Exception as e:
            messagebox.showerror("Embedding Error", str(e))
            return
        messagebox.showinfo("Success", f"Data successfully encrypted and embedded!\nSaved as: {self.output_path}")

    def open_extract_window(self):
        win = tk.Toplevel(self.root)
        win.title("Extract & Decrypt Hidden Text")
        win.geometry("700x550")

        frame = tk.Frame(win)
        frame.pack(fill="both", expand=True, padx=8, pady=8)

        img_sel_frame = tk.Frame(frame)
        img_sel_frame.pack(fill="x", pady=4)
        tk.Button(img_sel_frame, text="Select Encrypted Image", command=lambda: self.select_input_image_for_extract(win)).pack(side="left")
        self.extract_info_label = tk.Label(img_sel_frame, text="(No image selected)")
        self.extract_info_label.pack(side="left", padx=8)

        self.preview_label_ext = tk.Label(frame, text="No image preview", width=60, height=12, bd=1, relief="sunken")
        self.preview_label_ext.pack(pady=6)

        pw_frame = tk.Frame(frame)
        pw_frame.pack(fill="x", pady=4)
        tk.Label(pw_frame, text="Password:").pack(side="left")
        self.password_entry_ext = tk.Entry(pw_frame, show="*")
        self.password_entry_ext.pack(side="left", padx=6)

        tk.Button(frame, text="Extract & Decrypt", bg="#3498db", fg="white", command=self.action_extract_and_decrypt).pack(pady=6)

        tk.Label(frame, text="Decrypted text:").pack(anchor="w")
        self.decrypted_text_box = tk.Text(frame, height=8)
        self.decrypted_text_box.pack(fill="x", pady=(0,8))

        tk.Button(frame, text="Save Decrypted Text", command=self.save_decrypted_to_file).pack(pady=6)

    def select_input_image_for_extract(self, window):
        path = filedialog.askopenfilename(title="Select Encrypted Image", filetypes=[("PNG", "*.png")])
        if not path:
            return
        self.input_path = path
        img = Image.open(path)
        img.thumbnail((500, 350))
        self.extract_tkimg = ImageTk.PhotoImage(img)
        self.preview_label_ext.config(image=self.extract_tkimg, text="")
        self.extract_info_label.config(text=f"Selected: {path}")

    def action_extract_and_decrypt(self):
        if not self.input_path:
            messagebox.showerror("Error", "Select an encrypted image first.")
            return
        password = self.password_entry_ext.get().strip()
        if not password:
            messagebox.showerror("Error", "Enter the password.")
            return
        try:
            embedded = extract_data_from_image(self.input_path)
        except Exception as e:
            messagebox.showerror("Extraction Error", str(e))
            return
        try:
            plain = decrypt_with_password(password, embedded)
        except Exception as e:
            messagebox.showerror("Decryption Error", f"Failed to decrypt: {e}")
            return
        try:
            text = plain.decode('utf-8')
        except:
            text = repr(plain)
        self.decrypted_text_box.delete("1.0", "end")
        self.decrypted_text_box.insert("1.0", text)
        messagebox.showinfo("Success", "Data extracted and decrypted successfully!")

    def save_decrypted_to_file(self):
        content = self.decrypted_text_box.get("1.0", "end").strip()
        if not content:
            messagebox.showerror("Error", "No text to save.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text", "*.txt")])
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        messagebox.showinfo("Saved", f"Decrypted text saved to: {path}")


if __name__ == "__main__":
    root = tk.Tk()
    app = StegoApp(root)
    root.mainloop()
