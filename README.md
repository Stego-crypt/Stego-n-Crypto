# 🛡️ Stego-n-Crypto: Digital Content Verification System

![Android](https://img.shields.io/badge/Android-3DDC84?style=for-the-badge&logo=android&logoColor=white)
![Kotlin](https://img.shields.io/badge/Kotlin-0095D5?style=for-the-badge&logo=kotlin&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)

Stego-n-Crypto is a client-server cryptographic architecture designed to securely sign, embed, and verify the authenticity of digital media (Text, Images, and PDFs). By combining **RSA Digital Signatures** with **Steganography**, this system ensures that media not only proves its origins but also mathematically proves its content has not been tampered with.

## ✨ Core Features
* **Cryptographic Signatures:** Uses RSA key pairs to generate unforgeable digital signatures for media files.
* **Invisible Payloads:** Embeds metadata and signatures directly into the file's data stream (LSB steganography for images, zero-width characters for text) without altering the visual appearance.
* **Content Integrity Verification:** Utilizes SHA-256 and Perceptual Image Hashing (Hamming Distance) to detect even single-pixel alterations.
* **Newline-Agnostic Hashing:** Bulletproof cross-platform transport logic that survives OS-level metadata mutations.
* **Modern Mobile Client:** A sleek Android application built with Jetpack Compose, featuring an onboard SQLite scan history database and real-time Dark Mode support.

---

## 🏗️ System Architecture

1. **Frontend (Android Client):** Built entirely in Kotlin using Jetpack Compose. Handles file selection, UI rendering, history tracking (Room DB), and REST API communication via Retrofit.
2. **Backend (FastAPI Engine):** A high-performance Python server that receives media, extracts steganographic payloads, calculates cryptographic hashes, and verifies RSA signatures.
3. **Transport Layer:** Configured to utilize Ngrok secure tunneling, allowing real-time global mobile access to the local backend during demonstrations.

---

## 🚀 Quick Start / Demo Setup

### Prerequisites
* Python 3.10+
* Android Studio (Ladybug or newer)
* Ngrok Account & CLI

### 1. Backend Setup
Clone the repository and spin up the Python environment:
```bash
git clone [https://github.com/Stego-crypt/Stego-n-Crypto.git](https://github.com/Stego-crypt/Stego-n-Crypto.git)
cd Stego-n-Crypto/backend

# Install required cryptography and web libraries
pip install -r requirements.txt

# Start the FastAPI verification server
python server.py
