#!/bin/bash
set -e

echo "=========================================="
echo "  Invoice Automation – Single Command Run"
echo "=========================================="

# Check dependencies
if ! command -v tesseract &> /dev/null; then
    echo "❌ Tesseract OCR not found."
    echo "   Install: sudo apt-get install tesseract-ocr tesseract-ocr-jpn"
    echo "   Or:      brew install tesseract tesseract-lang"
    exit 1
fi

if ! python3 -c "import fitz" &> /dev/null; then
    echo "❌ Python dependencies not installed."
    echo "   Run: pip install -r requirements.txt"
    exit 1
fi

# Start API server in background
echo ""
echo "🔄 Starting Accounting API server..."
python3 accounting_api.py &
API_PID=$!

# Wait for API to become ready
echo "⏳ Waiting for API..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:8080/health > /dev/null 2>&1; then
        echo "✅ API is ready."
        break
    fi
    sleep 1
done

# Run the pipeline
echo ""
python3 main.py
EXIT_CODE=$?

# Cleanup
echo ""
echo "🛑 Stopping API server..."
kill $API_PID 2>/dev/null || true
wait $API_PID 2>/dev/null || true

exit $EXIT_CODE