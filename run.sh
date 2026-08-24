#!/bin/bash
set -e

echo "=========================================="
echo "  Invoice Automation – Single Command Run"
echo "=========================================="

# --- Pre-flight checks ---
if ! command -v tesseract &> /dev/null; then
    echo "❌ Tesseract OCR not found."
    echo "   Install: sudo apt-get install tesseract-ocr tesseract-ocr-jpn"
    exit 1
fi

if ! python3 -c "import fitz" &> /dev/null; then
    echo "❌ Python dependencies not installed."
    echo "   Run: pip install -r requirements.txt"
    exit 1
fi

if [ ! -f accounting_api.py ]; then
    echo "❌ accounting_api.py not found in current directory."
    exit 1
fi

# --- Kill any stale API process on port 8080 ---
if lsof -ti:8080 &> /dev/null; then
    echo "⚠️  Port 8080 already in use. Killing stale process..."
    kill $(lsof -ti:8080) 2>/dev/null || true
    sleep 2
fi

# --- Start API server in background ---
echo ""
echo "🔄 Starting Accounting API server..."
python3 accounting_api.py > /tmp/accounting_api.log 2>&1 &
API_PID=$!

# Ensure cleanup on exit (Ctrl+C, error, or normal completion)
cleanup() {
    echo ""
    echo "🛑 Stopping API server (PID $API_PID)..."
    kill $API_PID 2>/dev/null || true
    wait $API_PID 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# --- Wait for API to become ready (max 30 seconds) ---
echo "⏳ Waiting for API to be ready..."
READY=0
for i in $(seq 1 30); do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ]; then
        READY=1
        break
    fi
    # Show progress every 5 attempts to avoid spam
    if [ $((i % 5)) -eq 0 ]; then
        echo "   Attempt $i/30: HTTP $HTTP_CODE"
    fi
    sleep 1
done

if [ $READY -eq 0 ]; then
    echo "❌ API failed to start within 30 seconds."
    echo "   Last HTTP code: $HTTP_CODE"
    echo "   API log output:"
    cat /tmp/accounting_api.log 2>/dev/null || echo "   (no log available)"
    echo ""
    echo "   Try running manually: python3 accounting_api.py"
    exit 1
fi

echo "✅ API is ready (PID $API_PID)."

# --- Run the pipeline ---
echo ""
python3 main.py
EXIT_CODE=$?

# Cleanup happens automatically via trap
exit $EXIT_CODE
