import os
from dotenv import load_dotenv

load_dotenv()

# Accounting API
API_BASE_URL = "http://localhost:8080"
API_KEY = "demo-key-1234"

# Paths
INVOICE_DIR = "invoices"
OUTPUT_DIR = "output"

# LLM Configuration
# Option 1: Groq (Free tier, requires key)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq") 
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Option 2: Ollama (Local, no key needed)
# LLM_PROVIDER = "ollama"
# OLLAMA_URL = "http://localhost:11434/api/generate"
# OLLAMA_MODEL = "llama3.2"