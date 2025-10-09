"""Document chunker for intelligent text splitting."""

from typing import List, Dict, Any, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter


class DocumentChunker:
    """Class for chunking documents into smaller segments."""
    
    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 100):
        """Initialize chunker with configurable parameters.

        Args:
            chunk_size: Maximum size of each chunk in characters (default: 512)
            chunk_overlap: Number of characters to overlap between chunks (default: 100)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
    
    def chunk_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Chunk text into smaller segments with metadata.

        Args:
            text: Text to chunk
            metadata: Optional metadata to preserve in chunks

        Returns:
            List of dictionaries with 'text' and 'metadata' keys
        """
        if not text:
            return []
        
        # Split text into chunks
        text_chunks = self.splitter.split_text(text)
        
        # Create result with metadata
        chunks = []
        position = 0
        for i, chunk_text in enumerate(text_chunks):
            chunk_meta = metadata.copy() if metadata else {}
            chunk_meta.update({
                'chunk_index': i,
                'start_position': position,
                'end_position': position + len(chunk_text)
            })
            
            chunks.append({
                'text': chunk_text,
                'metadata': chunk_meta
            })
            
            # Update position for next chunk (accounting for overlap)
            position += len(chunk_text) - self.chunk_overlap
        
        return chunks
