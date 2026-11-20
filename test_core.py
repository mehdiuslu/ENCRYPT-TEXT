"""Run with:  py -m unittest -v"""
import hashlib
import os
import random
import struct
import tempfile
import unittest

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from PIL import Image

import core
from core import StegoError


def make_image(path, size=(64, 64), mode="RGB", seed=1):
    rnd = random.Random(seed)
    img = Image.new(mode, size)
    n = len(mode)
    px = [tuple(rnd.randrange(256) for _ in range(n)) for _ in range(size[0] * size[1])]
    img.putdata([p[0] for p in px] if n == 1 else px)
    img.save(path)


def legacy_blob(password: str, data: bytes) -> bytes:
    """Exactly what the first version of the tool produced."""
    salt = get_random_bytes(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000, dklen=32)
    c = AES.new(key, AES.MODE_EAX)
    ct, tag = c.encrypt_and_digest(data)
    return salt + c.nonce + tag + ct


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.p = lambda n: os.path.join(self.dir.name, n)

    def tearDown(self):
        self.dir.cleanup()

    def roundtrip(self, mode, text="Merhaba dünya — gizli mesaj ✅"):
        make_image(self.p("in.png"), mode=mode)
        core.encrypt_into_image(self.p("in.png"), text, "correct horse", self.p("out.png"))
        return core.decrypt_from_image(self.p("out.png"), "correct horse")

    def test_roundtrip_rgb(self):
        self.assertEqual(self.roundtrip("RGB"), "Merhaba dünya — gizli mesaj ✅")

    def test_roundtrip_rgba_keeps_alpha(self):
        self.assertEqual(self.roundtrip("RGBA"), "Merhaba dünya — gizli mesaj ✅")
        a = list(Image.open(self.p("in.png")).getchannel("A").getdata())
        b = list(Image.open(self.p("out.png")).getchannel("A").getdata())
        self.assertEqual(a, b)

    def test_palette_and_grayscale_sources(self):
        for mode in ("L", "P"):
            make_image(self.p("g.png"), mode="L")
            Image.open(self.p("g.png")).convert(mode).save(self.p("in.png"))
            core.encrypt_into_image(self.p("in.png"), "x" * 20, "password1", self.p("out.png"))
            self.assertEqual(core.decrypt_from_image(self.p("out.png"), "password1"), "x" * 20)

    def test_only_lsbs_change(self):
        make_image(self.p("in.png"))
        core.encrypt_into_image(self.p("in.png"), "hello world", "password1", self.p("out.png"))
        a = Image.open(self.p("in.png")).tobytes()
        b = Image.open(self.p("out.png")).tobytes()
        self.assertTrue(all(abs(x - y) <= 1 for x, y in zip(a, b)))

    def test_wrong_password(self):
        make_image(self.p("in.png"))
        core.encrypt_into_image(self.p("in.png"), "secret", "password1", self.p("out.png"))
        with self.assertRaisesRegex(StegoError, "Wrong password"):
            core.decrypt_from_image(self.p("out.png"), "password2")

    def test_image_without_hidden_data(self):
        make_image(self.p("plain.png"), size=(200, 200))
        with self.assertRaises(StegoError):
            core.decrypt_from_image(self.p("plain.png"), "password1")

    def test_tampered_image_is_detected(self):
        make_image(self.p("in.png"))
        core.encrypt_into_image(self.p("in.png"), "secret message", "password1", self.p("out.png"))
        img = Image.open(self.p("out.png"))
        raw = bytearray(img.tobytes())
        for i in range(32 * 3, 32 * 3 + 600, 3):   # flip carrier bits inside the ciphertext
            raw[i] ^= 1
        Image.frombytes("RGB", img.size, bytes(raw)).save(self.p("bad.png"))
        with self.assertRaises(StegoError):
            core.decrypt_from_image(self.p("bad.png"), "password1")

    def test_capacity(self):
        make_image(self.p("in.png"), size=(32, 32))
        cap = core.capacity_bytes(self.p("in.png"))
        self.assertEqual(cap, (32 * 32 * 3 - 32) // 8)
        blob = core.encrypt("password1", b"a" * (cap - 56))        # exactly fits
        core.embed(self.p("in.png"), blob, self.p("full.png"))
        self.assertEqual(core.decrypt("password1", core.extract(self.p("full.png"))), b"a" * (cap - 56))
        with self.assertRaisesRegex(StegoError, "too small"):
            core.embed(self.p("in.png"), blob + b"x", self.p("over.png"))

    def test_short_password_and_empty_text(self):
        make_image(self.p("in.png"))
        with self.assertRaises(StegoError):
            core.encrypt_into_image(self.p("in.png"), "hi", "short", self.p("o.png"))
        with self.assertRaises(StegoError):
            core.encrypt_into_image(self.p("in.png"), "", "password1", self.p("o.png"))

    def test_password_is_not_stripped(self):
        make_image(self.p("in.png"))
        core.encrypt_into_image(self.p("in.png"), "hi there", "  spaced pw  ", self.p("out.png"))
        with self.assertRaises(StegoError):
            core.decrypt_from_image(self.p("out.png"), "spaced pw")
        self.assertEqual(core.decrypt_from_image(self.p("out.png"), "  spaced pw  "), "hi there")

    def test_reads_images_from_the_first_version(self):
        make_image(self.p("in.png"))
        core.embed(self.p("in.png"), legacy_blob("oldpass1", "eski mesaj".encode()), self.p("old.png"))
        self.assertEqual(core.decrypt_from_image(self.p("old.png"), "oldpass1"), "eski mesaj")

    def test_absurd_iteration_count_is_refused(self):
        blob = core.MAGIC + struct.pack(">I", 4_000_000_000) + os.urandom(100)
        with self.assertRaises(StegoError):
            core.decrypt("password1", blob)

    def test_unreadable_file(self):
        with open(self.p("x.png"), "wb") as f:
            f.write(b"not an image")
        with self.assertRaises(StegoError):
            core.extract(self.p("x.png"))


if __name__ == "__main__":
    unittest.main()
