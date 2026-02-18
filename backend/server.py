from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
import uvicorn

# Import our Logic Engine
# This allows us to use the EXACT same logic as the CLI tool
try:
    from verifier_core import analyze_file
except ImportError:
    # Fallback if running from a different directory context
    from backend.verifier_core import analyze_file

app = FastAPI(
    title="StegoCrypto Verification API",
    description="Backend API for the Digital Content Verification System",
    version="1.0"
)

# --- CORS CONFIGURATION ---
# This allows mobile apps and other websites to access your server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (Safe for a demo project)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (POST, GET, etc.)
    allow_headers=["*"],
)

# Setup temporary storage for uploaded files
UPLOAD_DIR = "temp_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/")
def read_root():
    """
    Health Check Endpoint.
    Used to verify if the server is up and running.
    """
    return {
        "status": "online",
        "system": "StegoCrypto Backend",
        "version": "1.0.0"
    }

@app.post("/verify/")
async def verify_document(file: UploadFile = File(...)):
    """
    Main Verification Endpoint.
    1. Receives a file (Image/PDF/Text).
    2. Saves it temporarily.
    3. Runs the deep verification logic.
    4. Returns a detailed JSON report.
    5. Cleans up the temp file.
    """
    # 1. Generate unique filename to avoid collisions between users
    # We use UUIDs to ensure file_a.jpg doesn't overwrite file_b.jpg
    file_ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    temp_path = os.path.join(UPLOAD_DIR, unique_filename)

    try:
        # 2. THE BULLETPROOF ASYNC SAVE METHOD
        # Await the raw bytes straight from the network memory
        content = await file.read()
        
        # Save them strictly in binary mode to disk
        with open(temp_path, "wb") as buffer:
            buffer.write(content)

        # 3. CALL THE BRAIN (verifier_core.py)
        # This function does all the heavy lifting (Crypto, Hash, Stego)
        result = analyze_file(temp_path)
        
        # 4. Return the result as JSON
        # The Android app will parse this JSON to show Green/Red screens
        return JSONResponse(content=result)

    except Exception as e:
        # Graceful error handling
        return JSONResponse(
            content={
                "status": "error", 
                "message": f"Server Error: {str(e)}"
            }, 
            status_code=500
        )
    
    finally:
        # 5. Cleanup Protocol
        # Always delete the temp file to keep the server clean
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass

if __name__ == "__main__":
    # HOST 0.0.0.0 is critical for Android Emulators to see the server
    # PORT 8000 is the standard development port
    uvicorn.run(app, host="0.0.0.0", port=8000)