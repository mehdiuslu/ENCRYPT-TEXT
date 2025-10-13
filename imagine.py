import struct
from PIL import Image

INPUT_IMAGE_PATH = "input.png"
OUTPUT_IMAGE_PATH = "output.png"


def _bytes_to_bits(data: bytes):
    for byte in data:
        for i in range(7, -1, -1):
            yield (byte >> i) & 1


def embed_data_in_image(image_path: str, data: bytes, output_path: str):
    img = Image.open(in_path)
    if img.mode not in ('RGB', 'RGBA'):
        img = img.convert('RGB')
    pixels = list(img.getdata())

    length = len(data)
    header = struct.pack('>I', length)  # 4 byte uzunluk başlığı
    full = header + data

    bits = list(_bytes_to_bits(full))
    capacity = len(pixels) * 3
    if len(bits) > capacity:
        raise ValueError(f"Yeterli kapasite yok. Gerekli bit: {len(bits)}, kapasite: {capacity}")

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
    img_out.save(out_path)
    print(f"Data embedded into image and saved to {output_path}")


# Main execution
if __name__ == "__main__":
    try:
        with open("data_to_embed.bin", "rb") as f:
            data_to_embed = f.read()
        embed_data_in_image(INPUT_IMAGE_PATH, data_to_embed, OUTPUT_IMAGE_PATH)
    except FileNotFoundError as e:
        if "data_to_embed.bin" in str(e):
            print("Error: 'data_to_embed.bin' file not found. Please run the text encryption step first.")
        else:
            print(f"Error: {e}")
    except ValueError as e:
        print(f"Error: {e}")

