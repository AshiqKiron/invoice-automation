import os
from dotenv import load_dotenv

load_dotenv()

# Accounting API
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8080")
API_KEY = os.getenv("API_KEY", "demo-key-1234")

# Paths
INVOICE_DIR = os.getenv("INVOICE_DIR", "invoices")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")

# LLM - Default to Groq free tier; switch to "ollama" for fully local
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")