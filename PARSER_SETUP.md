# Document Parser Setup Guide

## Overview

Your system now has **hybrid document parsing** with:
- ✅ **Free parsers first** (Unstructured.io + OCR)
- ✅ **ADE API fallback** for complex documents (optional)
- ✅ Support for PDF, images, DOCX, and more

## 🚀 Quick Start

### 1. Install Free Parser Dependencies

```bash
# Basic installation (recommended)
pip install -r requirements.txt

# For PDF support, you may also need system dependencies:
# Ubuntu/Debian:
sudo apt-get install -y tesseract-ocr tesseract-ocr-vie poppler-utils

# macOS:
brew install tesseract poppler

# Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki
```

### 2. Basic Usage (Free Parsers Only)

```bash
# Parse a PDF document (uses free Unstructured.io)
python src/ingest.py --input data/LIGHTRAG.pdf

# Parse plain text (works as before)
python src/ingest.py --input data/vn_law_sample.txt
```

### 3. With ADE Fallback (Optional)

```bash
# Set your ADE API key as environment variable
export ADE_API_KEY="your_landing_ai_api_key"

# Or pass it directly
python src/ingest.py --input data/LIGHTRAG.pdf --ade-api-key "your_key"
```

## 📊 How It Works

```
┌─────────────────────────────────────────┐
│  Input: PDF, Image, DOCX, TXT          │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  Step 1: Try Free Parser               │
│  (Unstructured.io + OCR)               │
└──────────────┬──────────────────────────┘
               │
               ▼
        Quality Check
               │
        ┌──────┴──────┐
        │             │
     ✓ Good       ✗ Poor
        │             │
        │             ▼
        │   ┌─────────────────────┐
        │   │ Step 2: ADE Fallback│
        │   │ (if API key set)    │
        │   └─────────┬───────────┘
        │             │
        ▼             ▼
    ┌───────────────────────┐
    │  Extracted Text       │
    │  + Metadata           │
    └───────────────────────┘
```

## 🎯 Parser Selection Logic

The system automatically chooses the best parser:

| Document Type | Primary Parser | Fallback | Notes |
|--------------|----------------|----------|-------|
| `.txt` | Direct read | N/A | Instant |
| `.pdf` (text) | Unstructured | ADE | Fast, accurate |
| `.pdf` (scanned) | Unstructured+OCR | ADE | OCR enabled |
| `.jpg`, `.png` | Unstructured+OCR | ADE | Image processing |
| `.docx`, `.pptx` | Unstructured | ADE | Office formats |

## 💰 Cost Comparison

### Example: 100-page Legal Document

| Parser | Cost | Time | Quality |
|--------|------|------|---------|
| **Free (Unstructured.io)** | $0 | ~30-60s | ⭐⭐⭐⭐ |
| **ADE API** | $3-10 | ~20-40s | ⭐⭐⭐⭐⭐ |

**Cost savings**: ~99% reduction by using free parsers for most documents

## 🔧 Advanced Configuration

### Python API Usage

```python
from src.document_parser import DocumentParser

# Free parsers only
parser = DocumentParser(ade_api_key=None)
text, metadata = parser.parse_document("document.pdf")

# With ADE fallback
parser = DocumentParser(ade_api_key="your_key", use_ade_fallback=True)
text, metadata = parser.parse_document("complex_document.pdf")

# Force use of ADE
text, metadata = parser.parse_document("document.pdf", force_ade=True)

# Check which parser was used
print(f"Parser used: {parser.last_parser_used}")  # 'free', 'ade', or 'text'
```

### Quality Threshold

The system automatically detects if free parser quality is insufficient:
- Text too short (< 50 chars)
- Too many non-printable characters (> 30%)
- Extraction errors

When quality is insufficient, it automatically tries ADE fallback (if configured).

## 📦 Optional Enhancements

### 1. Faster PDF Processing (Marker)

```bash
pip install marker-pdf

# Use in code
from src.document_parser import parse_pdf_with_marker
text = parse_pdf_with_marker("document.pdf")
```

### 2. Advanced OCR (Surya)

```bash
pip install surya-ocr

# Use in code
from src.document_parser import parse_with_surya_ocr
text = parse_with_surya_ocr("scanned_page.jpg")
```

### 3. Enable ADE Fallback

```bash
# Install Landing AI library
pip install landingai

# Get API key from https://va.landing.ai/
# Set environment variable
export ADE_API_KEY="your_key_here"
```

## 🧪 Testing Your Setup

Test with your PDF document:

```bash
# Test free parser
python src/ingest.py --input data/LIGHTRAG.pdf

# Expected output:
# INFO:__main__:Parsing document: data/LIGHTRAG.pdf
# INFO:__main__:Attempting free parser for data/LIGHTRAG.pdf...
# INFO:document_parser:Parsing with Unstructured.io (high-res strategy)...
# INFO:document_parser:Quality check passed: 15234 chars, 0.98% printable
# INFO:__main__:✓ Successfully parsed with free tools
# INFO:__main__:Parser used: free
# Split into 45 chunks.
```

## 🐛 Troubleshooting

### "unstructured not found"
```bash
pip install "unstructured[pdf]" pillow pdfminer.six
```

### "tesseract not found"
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr tesseract-ocr-vie

# macOS
brew install tesseract
```

### Poor extraction quality
1. Check if document is scanned (image-based PDF)
2. Install Vietnamese language pack for Tesseract
3. Consider enabling ADE fallback for complex documents

### ADE API errors
- Verify API key is correct
- Check internet connection
- Review ADE credit balance at https://va.landing.ai/

## 📊 Monitoring Parser Usage

Track which parser is being used:

```python
import logging
logging.basicConfig(level=logging.INFO)

# Logs will show:
# - Which parser is being tried
# - Quality check results
# - Fallback triggers
# - Final parser used
```

## 🎯 Best Practices

1. **Start with free parsers** - They handle 90%+ of documents well
2. **Enable ADE fallback** - Only pays for complex documents that need it
3. **Monitor quality** - Check logs to see when fallback triggers
4. **Optimize costs** - Review which documents trigger ADE and improve free parser if needed
5. **Cache results** - Store parsed output to avoid re-processing

## 📚 Next Steps

1. Test with your Vietnamese legal PDFs
2. Monitor free vs. ADE usage ratio
3. Adjust quality thresholds if needed
4. Consider batch processing for large document sets
5. Integrate with your existing RAG pipeline

## Support

- Unstructured.io docs: https://unstructured-io.github.io/unstructured/
- Landing AI ADE docs: https://docs.landing.ai/ade/
- Issues: Check logs for detailed error messages
