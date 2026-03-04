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
```

### 2. Network Tunneling (For Mobile Access)

To allow the Android app to securely communicate with your local machine from any network, you need to set up a secure tunnel using Ngrok.

1. Create a free Ngrok account, install the CLI, and authenticate it.
2. Go to your Ngrok dashboard (Cloud Edge > Domains) and claim your free static domain.
3. Open a new terminal and run the tunnel using your specific domain:

```bash
ngrok http --domain=your-custom-domain.ngrok-free.app 8000
```

**Update the Android Code:** Before building the app, navigate to `app/src/main/java/com/example/stegocrypto/RetrofitClient.kt` and update the `BASE_URL` variable to match your new Ngrok domain:

```kotlin
// Inside RetrofitClient.kt
private const val BASE_URL = "[https://your-custom-domain.ngrok-free.app/](https://your-custom-domain.ngrok-free.app/)"
```

### 3. Frontend Setup (Android App)

1. Open Android Studio.
2. Select **Open** and navigate to the `StegoCrypto` folder inside this repository.
3. Allow Gradle to sync and download the required Android dependencies.
4. Go to **Build > Build Bundle(s) / APK(s) > Build APK(s)** to generate the executable.
5. Transfer the resulting `.apk` to your physical Android device and install it.

*(Note: Pre-built APKs are available in the **Releases** section of this repository for quick testing).*

