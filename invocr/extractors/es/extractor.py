"""
Spanish language extractor implementation.
This is a stub implementation for testing purposes.
"""

class SpanishExtractor:
    """Stub for Spanish extractor implementation"""
    
    def __init__(self):
        pass
        
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
