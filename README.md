🧠 ENCRYPT-TEXT  
Encrypt your text inside an image — AES-based secure steganography tool.

This project allows you to encrypt any text message using AES encryption and hide it inside a PNG image.
The hidden message can only be decrypted with the same password.

------------------------------------------------------------
⚙️ INSTALLATION
------------------------------------------------------------

🪟 FOR WINDOWS
------------------------------------------------------------
1️⃣ Make sure you have Python 3.9+ installed.  
   Check it with:
   python --version

2️⃣ Install required libraries:
   pip install pycryptodome pillow

3️⃣ Test the installation:
   python -c "from Crypto.Cipher import AES; from PIL import Image; print('Libraries OK ✅')"

------------------------------------------------------------
🐧 FOR LINUX (Ubuntu / Kali / Arch / Debian)
------------------------------------------------------------
1️⃣ If Python3 is not installed:
   sudo apt install python3 python3-pip -y

2️⃣ Install the required libraries:
   python3 -m pip install --user pycryptodome pillow

3️⃣ Test the installation:
   python3 -c "from Crypto.Cipher import AES; from PIL import Image; print('Libraries OK ✅')"

------------------------------------------------------------
📦 DEPENDENCIES
------------------------------------------------------------
• pycryptodome  → AES encryption and hashing  
• pillow        → PNG read/write for steganography

------------------------------------------------------------
🪄 HOW TO USE
------------------------------------------------------------
1️⃣ Clone this repository:
   git clone https://github.com/mehdiuslu/ENCRYPT-TEXT.git
   cd ENCRYPT-TEXT

2️⃣ Run the program:
   python main.py
   (or on Linux)
   python3 main.py

3️⃣ Follow the steps in the terminal:
   - Type the text you want to encrypt  
   - Choose a password (don’t forget it!)  
   - Select a .png image to embed the encrypted data  

4️⃣ Output:
   A new file named “encrypted_output.png” will be created.
   This file contains your AES-encrypted and hidden text.

------------------------------------------------------------
🔐 EXAMPLE
------------------------------------------------------------
Enter text to encrypt: Hello world!
Enter password: ********
Select image: input.png
✅ Encrypted image created: encrypted_output.png

------------------------------------------------------------
❗ TROUBLESHOOTING
------------------------------------------------------------
❌ ModuleNotFoundError: No module named 'Crypto'  
➡ pip install pycryptodome

❌ ImportError: No module named 'PIL'  
➡ pip install pillow

❌ UnicodeEncodeError  
➡ Save your file as UTF-8

------------------------------------------------------------
📜 LICENSE
------------------------------------------------------------
Free & Open Source  
Developed by mehdiuslu 🧠

