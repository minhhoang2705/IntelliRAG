"""Document chunker for intelligent text splitting."""


class DocumentChunker:
    """Class for chunking documents into smaller segments."""
    
    def __init__(self):
        """Initialize chunker with default parameters."""
        self.chunk_size = 512
        self.chunk_overlap = 100
