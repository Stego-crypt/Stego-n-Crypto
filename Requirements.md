# Problem Statement
> Fake documents and images are being circulated as if they came from official government sources. The public has no simple way to check authenticity.

# Proposed Solution
Embed a cryptographically signed authenticity token into media using robust steganography so anyone can verify it with an app. The cryptographic paradigm used is Asymmetric Encryption. The content of the file will be hashed and then encoded using an entity's private key, the recepient can then use the public key to verify authenticity.

# Scope
## In Scope
- Can embedd keys in Images, PDFs, Text
- Make use of Android share menu
- Encode above stated media with cryptographic keys
## Out of Scope
- Video steganography
- Audio steganography

## Functional Requirements (MUST)

### FR1 — Publish & Sign
The system shall accept an image and metadata (issuer_id, timestamp, doc_id) and create a signed payload using a private key (RSA-2048 or ECDSA-P256).

### FR2 — Embed Watermark
The system shall embed the signed payload into the image using DCT-based watermarking with ECC applied to the payload before embedding.

### FR3 — Extract & Verify
The verifier shall extract the embedded payload from any supplied image and verify the signature using the public key.

### FR4 — Verification Result UX
The verifier shall display one of:
- **VERIFIED**
- **INVALID_SIGNATURE / TAMPERED**
- **NO_TOKEN_FOUND**

Metadata (issuer, timestamp) must be shown on **VERIFIED** results.

### FR5 — Basic Robustness Support
The system shall tolerate:
- JPEG recompression (quality ≥ 80)  
- Downscaling to ~75% and re-upscaling  
- Mild cropping (≤ 10% border)

A minimum extraction success rate of **≥ 85%** under these conditions must be demonstrated.

### FR6 — Offline Verification
Verification must be possible offline if the public key is preloaded into the verifier.

### FR7 — Automated Test Harness
Scripts must be provided to:
- Generate transformed test images
- Compute extraction success rate
- Compute PSNR and SSIM for perceptual quality

---

## Non-Functional Requirements (NFR)

### NFR1 (MUST) — Performance
Verification (extract + signature check) shall complete within **3 seconds** on midrange hardware.

### NFR2 (MUST) — Perceptual Invisibility
Watermarked images must have:
- PSNR ≥ **38 dB** or  
- SSIM ≥ **0.95**

### NFR3 (SHOULD) — Robustness
≥ 85% extraction success under JPEG 80 and 75% resize.

### NFR4 (SHOULD) — Usability
Verification shall require **≤ 3 steps** from user (upload/screenshot/share → result).

### NFR5 (MUST) — Security (Prototype Level)
- Only established crypto libraries may be used.  
- Private keys must not be committed to the repository.  
- Example key-generation instructions provided separately.

### NFR6 (COULD) — Portability
Stego engine should run on Linux/Windows; verifier may be web or mobile.

---

## Constraints & Out-of-Scope
- No real government integration or production-grade PKI.  
- No video/audio watermarking.  
- No OCR pipeline for print-scan workflows (optional future work).  
- No advanced adversarial attack resistance (beyond basic robustness).

---

## Data & Payload Format (Recommended)

### Payload JSON (before signing):
```json
{
  "doc_hash": "<SHA256>",
  "issuer": "<issuer_id>",
  "timestamp": "YYYY-MM-DDTHH:MM:SSZ",
  "doc_id": "<optional>"
}

