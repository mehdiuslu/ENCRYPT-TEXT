"""StegoCrypt - hide AES-encrypted text inside a PNG image.   Run:  py main.py"""
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

import core
from core import StegoError

BG, PANEL, TEXT, MUTED = "#efede8", "#ffffff", "#232323", "#6b6760"
ACCENT, ACCENT_DK, DANGER, OK, LINE = "#2f5d62", "#244a4e", "#a33a2c", "#3b7a4f", "#cfcac0"
IMAGE_TYPES = [("Images", "*.png *.bmp *.jpg *.jpeg *.webp *.gif *.tif *.tiff"), ("All files", "*.*")]
LOSSLESS_TYPES = [("PNG / BMP (lossless)", "*.png *.bmp"), ("All files", "*.*")]
PREVIEW = (380, 300)


def preview_image(path):
    img = Image.open(path)
    img.thumbnail(PREVIEW)
    return ImageTk.PhotoImage(img.convert("RGBA"))


class ImagePane(ttk.Frame):
    """Framed preview with a caption line."""

    def __init__(self, master, placeholder):
        super().__init__(master)
        holder = tk.Frame(self, width=PREVIEW[0], height=PREVIEW[1], bg="#e4e1da",
                          highlightthickness=1, highlightbackground=LINE)
        holder.pack()
        holder.pack_propagate(False)          # fixed pixel size, whatever the image inside
        self.box = tk.Label(holder, text=placeholder, fg=MUTED, bg="#e4e1da", font=("Segoe UI", 10))
        self.box.pack(fill="both", expand=True)
        self.caption = ttk.Label(self, text="", style="Muted.TLabel", anchor="w")
        self.caption.pack(fill="x", pady=(6, 0))
        self._img = None

    def show(self, path, caption):
        self._img = preview_image(path)
        self.box.config(image=self._img, text="")
        self.caption.config(text=caption)


class App:
    def __init__(self, root):
        self.root = root
        root.title("StegoCrypt")
        root.geometry("940x640")
        root.minsize(820, 580)
        root.configure(bg=BG)
        self.src = self.out = self.enc_img = None
        self.cap = 0
        self._style()

        head = tk.Frame(root, bg=ACCENT)
        head.pack(fill="x")
        tk.Label(head, text="StegoCrypt", bg=ACCENT, fg="white", font=("Segoe UI Semibold", 16)).pack(side="left", padx=18, pady=10)
        tk.Label(head, text="AES-256 encrypted text, hidden in the pixels of a PNG", bg=ACCENT, fg="#c9dcdc",
                 font=("Segoe UI", 10)).pack(side="left", pady=10)

        self.status = tk.StringVar(value="Choose an image to begin.")
        self.status_lbl = tk.Label(root, textvariable=self.status, bg=BG, fg=MUTED, anchor="w", font=("Segoe UI", 9))
        self.status_lbl.pack(side="bottom", fill="x", padx=18, pady=(0, 8))

        self.nb = ttk.Notebook(root)
        self.nb.pack(fill="both", expand=True, padx=14, pady=(12, 6))
        hide, reveal = ttk.Frame(self.nb, padding=16), ttk.Frame(self.nb, padding=16)
        self.nb.add(hide, text="  Hide text  ")
        self.nb.add(reveal, text="  Reveal text  ")
        self._build_hide(hide)
        self._build_reveal(reveal)
        root.bind("<Control-Return>", lambda e: self.do_hide() if self.nb.index("current") == 0 else self.do_reveal())

    # ------------------------------------------------------------ styling --
    def _style(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure(".", background=BG, foreground=TEXT, font=("Segoe UI", 10))
        s.configure("TFrame", background=BG)
        s.configure("TLabel", background=BG)
        s.configure("Muted.TLabel", foreground=MUTED, font=("Segoe UI", 9))
        s.configure("H.TLabel", font=("Segoe UI Semibold", 10))
        s.configure("TNotebook", background=BG, borderwidth=0)
        s.configure("TNotebook.Tab", padding=(6, 7), background="#e3e0d9", foreground=MUTED, borderwidth=0)
        s.map("TNotebook.Tab", background=[("selected", BG)], foreground=[("selected", ACCENT)])
        s.configure("TButton", padding=(12, 7), background="#e3e0d9", borderwidth=1, bordercolor=LINE, focuscolor=BG)
        s.map("TButton", background=[("active", "#d9d5cc")])
        s.configure("Accent.TButton", background=ACCENT, foreground="white", bordercolor=ACCENT, padding=(16, 9),
                    font=("Segoe UI Semibold", 10))
        s.map("Accent.TButton", background=[("active", ACCENT_DK), ("disabled", "#9fb5b7")])
        s.configure("TEntry", fieldbackground=PANEL, bordercolor=LINE, padding=6)
        s.configure("TCheckbutton", background=BG)
        s.configure("Cap.Horizontal.TProgressbar", troughcolor="#ded9ce", background=OK, bordercolor=BG, thickness=8)
        s.configure("Over.Horizontal.TProgressbar", troughcolor="#ded9ce", background=DANGER, bordercolor=BG, thickness=8)

    def say(self, msg, kind="info"):
        self.status.set(msg)
        self.status_lbl.config(fg={"info": MUTED, "ok": OK, "error": DANGER}[kind])

    def _text_box(self, master, height, state="normal"):
        wrap = ttk.Frame(master)
        t = tk.Text(wrap, height=height, wrap="word", bg=PANEL, fg=TEXT, relief="flat", font=("Segoe UI", 10),
                    highlightthickness=1, highlightbackground=LINE, highlightcolor=ACCENT, padx=8, pady=6, undo=True)
        sb = ttk.Scrollbar(wrap, command=t.yview)
        t.config(yscrollcommand=sb.set, state=state)
        sb.pack(side="right", fill="y")
        t.pack(side="left", fill="both", expand=True)
        return wrap, t

    def _password(self, master, label, show_var):
        ttk.Label(master, text=label, style="H.TLabel").pack(anchor="w", pady=(10, 3))
        e = ttk.Entry(master, show="•")
        e.pack(fill="x")
        show_var.trace_add("write", lambda *_: e.config(show="" if show_var.get() else "•"))
        return e

    # ---------------------------------------------------------- hide tab --
    def _build_hide(self, f):
        left, right = ttk.Frame(f), ttk.Frame(f)
        left.pack(side="left", fill="y", padx=(0, 18))
        right.pack(side="left", fill="both", expand=True)

        self.pane_src = ImagePane(left, "No image selected")
        self.pane_src.pack(fill="both", expand=True)
        ttk.Button(left, text="Choose image…", command=self.pick_source).pack(anchor="w", pady=(10, 4))
        self.cap_bar = ttk.Progressbar(left, style="Cap.Horizontal.TProgressbar", maximum=100)
        self.cap_bar.pack(fill="x", pady=(6, 2))
        self.cap_lbl = ttk.Label(left, text="Capacity: -", style="Muted.TLabel")
        self.cap_lbl.pack(anchor="w")

        ttk.Label(right, text="Text to hide", style="H.TLabel").pack(anchor="w", pady=(0, 3))
        wrap, self.msg = self._text_box(right, 7)
        wrap.pack(fill="both", expand=True)
        self.msg.bind("<<Modified>>", self._msg_changed)

        self.show_pw = tk.BooleanVar()
        self.pw1 = self._password(right, f"Password (at least {core.MIN_PASSWORD_LEN} characters)", self.show_pw)
        ttk.Label(right, text="Repeat password", style="H.TLabel").pack(anchor="w", pady=(10, 3))
        self.pw2 = ttk.Entry(right, show="•")
        self.pw2.pack(fill="x")
        self.show_pw.trace_add("write", lambda *_: self.pw2.config(show="" if self.show_pw.get() else "•"))
        ttk.Checkbutton(right, text="Show passwords", variable=self.show_pw).pack(anchor="w", pady=(8, 0))
        ttk.Label(right, text="There is no password recovery: lose it and the text is gone.", style="Muted.TLabel").pack(anchor="w", pady=(2, 0))

        row = ttk.Frame(right)
        row.pack(fill="x", pady=(14, 0))
        self.go_hide = ttk.Button(row, text="Encrypt & hide", style="Accent.TButton", command=self.do_hide)
        self.go_hide.pack(side="left")
        ttk.Label(row, text="Ctrl+Enter", style="Muted.TLabel").pack(side="left", padx=10)

    def pick_source(self):
        path = filedialog.askopenfilename(title="Choose a cover image", filetypes=IMAGE_TYPES)
        if not path:
            return
        try:
            self.pane_src.show(path, os.path.basename(path))
            self.cap = core.capacity_bytes(path)
        except Exception as e:
            self.say(f"Cannot open that image: {e}", "error")
            return
        self.src, self.out = path, None
        self._update_capacity()
        self.say(f"Image loaded. Up to {self.cap:,} bytes can be hidden in it.")

    def _msg_changed(self, _=None):
        if self.msg.edit_modified():
            self.msg.edit_modified(False)
            self._update_capacity()

    def _update_capacity(self):
        if not self.src:
            return
        need = len(self.msg.get("1.0", "end-1c").encode("utf-8")) + 56  # 56 = format header, salt, nonce, tag
        pct = min(100, 100 * need / max(1, self.cap))
        over = need > self.cap
        self.cap_bar.config(value=pct, style="Over.Horizontal.TProgressbar" if over else "Cap.Horizontal.TProgressbar")
        self.cap_lbl.config(text=f"Uses {need:,} of {self.cap:,} bytes" + ("  -  too large, pick a bigger image" if over else ""),
                            foreground=DANGER if over else MUTED)

    def do_hide(self):
        text = self.msg.get("1.0", "end-1c")
        if not self.src:
            return self.say("Choose a cover image first.", "error")
        if not text.strip():
            return self.say("Type the text you want to hide.", "error")
        if self.pw1.get() != self.pw2.get():
            return self.say("The two passwords do not match.", "error")
        if not self.out:
            base = os.path.splitext(os.path.basename(self.src))[0] + "_hidden.png"
            self.out = filedialog.asksaveasfilename(title="Save the new image as", defaultextension=".png",
                                                    initialfile=base, filetypes=[("PNG", "*.png")]) or None
            if not self.out:
                return
        if os.path.abspath(self.out) == os.path.abspath(self.src):
            self.out = None
            return self.say("Do not overwrite the original image - choose another file name.", "error")
        self.root.config(cursor="watch")
        self.root.update_idletasks()
        try:
            n = core.encrypt_into_image(self.src, text, self.pw1.get(), self.out)
        except StegoError as e:
            return self.say(str(e), "error")
        except OSError as e:
            return self.say(f"Could not write the file: {e}", "error")
        finally:
            self.root.config(cursor="")
        self.say(f"Done - {n:,} encrypted bytes hidden in {os.path.basename(self.out)}.", "ok")
        messagebox.showinfo("StegoCrypt", f"Saved:\n{self.out}\n\nShare it as a file, not through apps that re-compress images.")
        self.out = None

    # -------------------------------------------------------- reveal tab --
    def _build_reveal(self, f):
        left, right = ttk.Frame(f), ttk.Frame(f)
        left.pack(side="left", fill="y", padx=(0, 18))
        right.pack(side="left", fill="both", expand=True)

        self.pane_enc = ImagePane(left, "No image selected")
        self.pane_enc.pack(fill="both", expand=True)
        ttk.Button(left, text="Choose image…", command=self.pick_encrypted).pack(anchor="w", pady=(10, 0))

        self.show_pw2 = tk.BooleanVar()
        self.pw_ext = self._password(right, "Password", self.show_pw2)
        self.pw_ext.bind("<Return>", lambda e: self.do_reveal())
        ttk.Checkbutton(right, text="Show password", variable=self.show_pw2).pack(anchor="w", pady=(8, 0))
        self.go_rev = ttk.Button(right, text="Reveal text", style="Accent.TButton", command=self.do_reveal)
        self.go_rev.pack(anchor="w", pady=(14, 12))

        ttk.Label(right, text="Hidden text", style="H.TLabel").pack(anchor="w", pady=(0, 3))
        wrap, self.result = self._text_box(right, 7, state="disabled")
        wrap.pack(fill="both", expand=True)
        row = ttk.Frame(right)
        row.pack(fill="x", pady=(10, 0))
        ttk.Button(row, text="Copy", command=self.copy_result).pack(side="left")
        ttk.Button(row, text="Save as .txt…", command=self.save_result).pack(side="left", padx=8)

    def pick_encrypted(self):
        path = filedialog.askopenfilename(title="Choose the image with hidden text", filetypes=LOSSLESS_TYPES)
        if not path:
            return
        try:
            self.pane_enc.show(path, os.path.basename(path))
        except Exception as e:
            return self.say(f"Cannot open that image: {e}", "error")
        self.enc_img = path
        self._set_result("")
        self.say("Enter the password and press Reveal.")

    def _set_result(self, text):
        self.result.config(state="normal")
        self.result.delete("1.0", "end")
        self.result.insert("1.0", text)
        self.result.config(state="disabled")

    def do_reveal(self):
        if not self.enc_img:
            return self.say("Choose the image first.", "error")
        if not self.pw_ext.get():
            return self.say("Enter the password.", "error")
        self.root.config(cursor="watch")
        self.root.update_idletasks()
        try:
            text = core.decrypt_from_image(self.enc_img, self.pw_ext.get())
        except StegoError as e:
            self._set_result("")
            return self.say(str(e), "error")
        finally:
            self.root.config(cursor="")
        self._set_result(text)
        self.say(f"Decrypted {len(text):,} characters.", "ok")

    def copy_result(self):
        text = self.result.get("1.0", "end-1c")
        if text:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.say("Copied to the clipboard.", "ok")

    def save_result(self):
        text = self.result.get("1.0", "end-1c")
        if not text:
            return self.say("Nothing to save yet.", "error")
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text", "*.txt")])
        if path:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
            self.say(f"Saved {os.path.basename(path)}.", "ok")


def main():
    try:  # crisp text on high-DPI Windows screens
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
