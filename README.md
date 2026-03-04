# 🔐 StegoCrypto: Digital Content Verification System

![Android](https://img.shields.io/badge/Android-3DDC84?style=for-the-badge&logo=android&logoColor=white)
![Kotlin](https://img.shields.io/badge/Kotlin-0095D5?&style=for-the-badge&logo=kotlin&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)

StegoCrypto is a full-stack, distributed application designed to mathematically verify the authenticity and integrity of digital media (Text, Images, and PDFs). 

By combining **RSA Public-Key Cryptography** with **Steganography**, this system allows authorities to embed invisible, tamper-proof cryptographic signatures directly inside files. The accompanying native Android application allows users to scan these files and instantly verify their origin and ensure they have not been altered by malicious actors.

## ✨ Key Features
* **Multi-Format Support:** Secures and verifies `.txt`, `.jpg`, `.png`, and `.pdf` files.
* **Cryptographic Tamper Detection:** Utilizes SHA-256 hashing and Perceptual Image Hashing (Hamming Distance) to detect even a single byte or pixel of unauthorized modification.
* **Newline-Agnostic Processing:** Robust backend architecture that survives cross-platform transport mutations (Windows CRLF vs. Linux LF) without throwing false-positive tamper alerts.
* **Modern Android UI:** Built entirely in Jetpack Compose, featuring an adaptive Material Design 3 interface with full System Dark Mode support.
* **High-Concurrency Backend:** Powered by Python's FastAPI, capable of handling simultaneous verification requests from multiple mobile clients over secure cloud tunnels.

## 🏗️ Architecture Stack
| Component | Technology | Description |
| :--- | :--- | :--- |
| **Frontend** | Kotlin, Jetpack Compose | Native Android Application |
| **Backend API** | Python, FastAPI | High-performance async REST API |
| **Cryptography** | `cryptography`, `hashlib` | RSA Signatures and SHA-256 Hashing |
| **Steganography** | `stegano`, `PyPDF2` | Invisible payload embedding |
| **Network** | Retrofit, Ngrok | Secure HTTP tunneling and API consumption |
| **Database** | Room (SQLite) | Local device scanning history |

---

## 🚀 Installation & Setup

### 1. Backend Setup (Local Server)
Ensure you have Python 3.9+ installed on your machine.

```bash
# Clone the repository
git clone [https://github.com/Stego-crypt/Stego-n-Crypto.git](https://github.com/Stego-crypt/Stego-n-Crypto.git)
cd Stego-n-Crypto/backend

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate

# Install the required dependencies
pip install -r requirements.txt

# Start the FastAPI Server
uvicorn server:app --host 0.0.0.0 --port 8000
