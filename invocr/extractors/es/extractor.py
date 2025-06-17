"""
Spanish language extractor implementation.
This is a stub implementation for testing purposes.
"""

class SpanishExtractor:
    """Stub for Spanish extractor implementation"""
    
    def __init__(self, languages=None):
        """Initialize the Spanish extractor with supported languages.
        
        Args:
            languages: List of language codes this extractor supports (default: ['es'])
        """
        self.languages = languages or ['es']
        
    def extract(self, text: str) -> dict:
        """
        Extract structured data from Spanish text.
        
        Args:
            text: Input text to extract data from
            
        Returns:
            Dictionary with extracted data
        """
        return {
            'text': text,
            'language': 'es',
            'entities': [],
            'intent': None,
            'confidence': 0.0
        }
