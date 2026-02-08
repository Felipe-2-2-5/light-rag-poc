"""
Document Parser with Free Solutions + ADE Fallback
Tries free parsers first (Unstructured.io + Surya OCR), falls back to ADE API for complex documents.
"""
import os
import logging
from typing import Tuple, Dict, Optional
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Download required NLTK resources for Unstructured.io
try:
    import nltk
    nltk.download('punkt_tab', quiet=True)
    nltk.download('averaged_perceptron_tagger_eng', quiet=True)
except Exception as e:
    logger.warning(f"Could not download NLTK resources: {e}")


class DocumentParser:
    """Hybrid document parser with free and paid options"""
    
    def __init__(self, ade_api_key: Optional[str] = None, use_ade_fallback: bool = True):
        """
        Initialize document parser with optional ADE fallback
        
        Args:
            ade_api_key: Landing AI API key for ADE fallback (optional)
            use_ade_fallback: Whether to use ADE as fallback for complex docs
        """
        self.ade_api_key = ade_api_key
        self.use_ade_fallback = use_ade_fallback and ade_api_key is not None
        
        # Track which parser was used
        self.last_parser_used = None
        
    def parse_document(self, file_path: str, force_ade: bool = False) -> Tuple[str, Optional[Dict]]:
        """
        Parse document using free solutions first, ADE as fallback
        
        Args:
            file_path: Path to document file
            force_ade: Force use of ADE API (skip free parsers)
            
        Returns:
            Tuple of (text_content, structured_metadata)
        """
        file_ext = Path(file_path).suffix.lower()
        
        # For plain text, just read directly
        if file_ext == '.txt':
            return self._parse_text(file_path)
        
        # Try free solutions first unless forced to use ADE
        free_parser_error = None
        if not force_ade:
            try:
                logger.info(f"Attempting free parser for {file_path}...")
                text, metadata = self._parse_with_free_tools(file_path)
                
                # Check if extraction quality is sufficient
                if self._is_quality_sufficient(text, metadata):
                    self.last_parser_used = "free"
                    logger.info(f"✓ Successfully parsed with free tools")
                    return text, metadata
                else:
                    logger.warning("Free parser quality insufficient, trying ADE fallback...")
                    
            except Exception as e:
                free_parser_error = e
                logger.warning(f"Free parser failed: {e}, trying ADE fallback...")
        
        # Fallback to ADE if available
        if self.use_ade_fallback:
            try:
                logger.info(f"Using ADE API for {file_path}...")
                text, metadata = self._parse_with_ade(file_path)
                self.last_parser_used = "ade"
                logger.info(f"✓ Successfully parsed with ADE")
                return text, metadata
            except Exception as e:
                logger.error(f"ADE parser also failed: {e}")
                raise
        else:
            # Provide detailed error message with the actual free parser error
            error_msg = f"Free parser failed and ADE fallback not available.\n\n"
            if free_parser_error:
                error_msg += f"Free parser error: {str(free_parser_error)}\n\n"
            error_msg += "To fix this:\n"
            error_msg += "1. Install Unstructured dependencies: pip install 'unstructured[pdf]' pillow pytesseract\n"
            error_msg += "2. Or set ADE_API_KEY environment variable to enable paid fallback"
            raise ValueError(error_msg)
    
    def _parse_text(self, file_path: str) -> Tuple[str, None]:
        """Parse plain text file"""
        with open(file_path, encoding='utf-8') as f:
            text = f.read()
        self.last_parser_used = "text"
        return text, None
    
    def _parse_with_free_tools(self, file_path: str) -> Tuple[str, Dict]:
        """
        Parse using free tools: Unstructured.io with OCR support
        
        This is the primary free solution that handles:
        - PDFs (text and scanned)
        - Images (PNG, JPG)
        - Office documents (DOCX, PPTX)
        """
        try:
            from unstructured.partition.auto import partition
            from unstructured.staging.base import elements_to_json
        except ImportError:
            raise ImportError(
                "Unstructured.io not installed. Run: pip install unstructured[all-docs] "
                "or: pip install 'unstructured[pdf]' pillow pdfminer.six"
            )
        
        # Parse with high-resolution strategy for better accuracy
        logger.info("Parsing with Unstructured.io (high-res strategy)...")
        elements = partition(
            filename=file_path,
            strategy="hi_res",  # Better accuracy, slower
            languages=["vie", "eng"],  # Vietnamese + English
            include_page_breaks=True
        )
        
        # Extract text with page number annotation
        text_parts = []
        page_map = []  # Track which text belongs to which page
        current_position = 0
        
        for element in elements:
            element_text = str(element)
            if element_text.strip():
                # Get page number from element metadata if available
                page_num = None
                if hasattr(element, 'metadata') and element.metadata:
                    page_num = getattr(element.metadata, 'page_number', None)
                
                text_parts.append(element_text)
                
                # Track page mapping
                page_map.append({
                    "start": current_position,
                    "end": current_position + len(element_text),
                    "page": page_num,
                    "element_type": type(element).__name__
                })
                
                current_position += len(element_text) + 2  # +2 for \n\n
        
        text = "\n\n".join(text_parts)
        
        # Create structured metadata with page mapping
        metadata = {
            "parser": "unstructured",
            "num_elements": len(elements),
            "element_types": [type(el).__name__ for el in elements],
            "has_tables": any("Table" in type(el).__name__ for el in elements),
            "page_map": page_map,  # NEW: Page number mapping
            "total_pages": max([pm.get('page', 0) or 0 for pm in page_map], default=0)
        }
        
        return text, metadata
    
    def _parse_with_ade(self, file_path: str) -> Tuple[str, Dict]:
        """
        Parse using Landing AI's ADE API
        Requires: pip install landingai
        """
        if not self.ade_api_key:
            raise ValueError("ADE_API_KEY not provided")
        
        try:
            from landingai.parse import ParseService
        except ImportError:
            raise ImportError("Landing AI library not installed. Run: pip install landingai")
        
        parser = ParseService(api_key=self.ade_api_key)
        result = parser.parse(file_path=file_path)
        
        # Extract markdown text
        text = result.markdown
        
        # Store full JSON response for advanced use
        metadata = {
            "parser": "ade",
            "json_data": result.json if hasattr(result, 'json') else None,
            "has_visual_grounding": True
        }
        
        return text, metadata
    
    def _is_quality_sufficient(self, text: str, metadata: Optional[Dict]) -> bool:
        """
        Check if free parser extraction quality is sufficient
        
        Criteria:
        - Extracted text is not empty
        - Text length is reasonable (> 50 chars)
        - Not too many parse errors
        """
        if not text or len(text.strip()) < 50:
            logger.info(f"Quality check failed: text too short ({len(text)} chars)")
            return False
        
        # Check for common extraction issues
        # If text is mostly garbled or has too many special chars, quality is low
        printable_ratio = sum(c.isprintable() or c.isspace() for c in text) / len(text)
        if printable_ratio < 0.7:
            logger.info(f"Quality check failed: too many non-printable chars ({printable_ratio:.2%})")
            return False
        
        logger.info(f"Quality check passed: {len(text)} chars, {printable_ratio:.2%} printable")
        return True


def parse_document(file_path: str, ade_api_key: Optional[str] = None) -> Tuple[str, Optional[Dict]]:
    """
    Convenience function to parse a document with hybrid approach
    
    Args:
        file_path: Path to document file
        ade_api_key: Optional Landing AI API key for fallback
        
    Returns:
        Tuple of (text_content, metadata)
    """
    parser = DocumentParser(ade_api_key=ade_api_key)
    return parser.parse_document(file_path)


# Alternative: Use Marker-PDF for faster PDF processing
def parse_pdf_with_marker(file_path: str) -> str:
    """
    Fast PDF to Markdown conversion using Marker
    Requires: pip install marker-pdf
    """
    try:
        from marker.convert import convert_single_pdf
    except ImportError:
        raise ImportError("Marker not installed. Run: pip install marker-pdf")
    
    full_text, images, metadata = convert_single_pdf(
        file_path,
        langs=["vi"],  # Vietnamese
        batch_multiplier=1
    )
    
    return full_text


# Alternative: Use Surya for OCR on image-heavy documents
def parse_with_surya_ocr(image_path: str) -> str:
    """
    OCR using Surya (better than Tesseract for complex layouts)
    Requires: pip install surya-ocr
    """
    try:
        from surya.ocr import run_ocr
        from surya.model.detection.segformer import load_model as load_det_model, load_processor as load_det_processor
        from surya.model.recognition.model import load_model as load_rec_model
        from surya.model.recognition.processor import load_processor as load_rec_processor
        from PIL import Image
    except ImportError:
        raise ImportError("Surya OCR not installed. Run: pip install surya-ocr")
    
    # Load models (cache these in production)
    det_model, det_processor = load_det_model(), load_det_processor()
    rec_model, rec_processor = load_rec_model(), load_rec_processor()
    
    # Run OCR
    image = Image.open(image_path)
    predictions = run_ocr(
        [image],
        [["vi", "en"]],  # Vietnamese + English
        det_model,
        det_processor,
        rec_model,
        rec_processor
    )
    
    # Extract text
    text = "\n".join([line.text for line in predictions[0].text_lines])
    return text
