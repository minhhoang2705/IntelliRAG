"""Document chunker for intelligent text splitting."""

from typing import List, Dict, Any, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter
import logging
import time


logger = logging.getLogger(__name__)


class HybridChunker(RecursiveCharacterTextSplitter):
    """Token-aware chunker that extends LangChain's RecursiveCharacterTextSplitter."""

    def __init__(self, tokenizer, max_tokens, overlap_tokens):
        """Initialize with tokenizer support."""
        self.tokenizer = tokenizer

        # Token-based length function
        def token_length(text: str) -> int:
            return len(tokenizer.encode(text))

        super().__init__(
            chunk_size=max_tokens,
            chunk_overlap=overlap_tokens,
            length_function=token_length,
            separators=["\n\n", "\n", ". ", " ", ""],
            is_separator_regex=False,
        )


class DocumentChunker:
    """Class for chunking documents into smaller segments."""

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 100,
        chunker_type: str = "langchain",
        model_id: str = "sentence-transformers/all-MiniLM-L6-v2"
    ):
        """Initialize chunker with configurable parameters.

        Args:
            chunk_size: Maximum size of each chunk in characters (default: 512)
            chunk_overlap: Number of characters to overlap between chunks (default: 100)
            chunker_type: Type of chunker to use ("langchain", "hybrid", "hierarchical") (default: "langchain")
            model_id: HuggingFace model ID for tokenization (default: all-MiniLM-L6-v2)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.chunker_type = chunker_type
        self.model_id = model_id

        # Initialize chunker based on type
        if chunker_type == "hybrid":
            from transformers import AutoTokenizer

            start_time = time.time()
            self.tokenizer = AutoTokenizer.from_pretrained(model_id)
            load_time = time.time() - start_time

            logger.info(
                f"Loaded tokenizer for hybrid chunker",
                extra={'extra_data': {
                    'model_id': model_id,
                    'tokenizer_load_time': round(load_time, 3)
                }}
            )

            self.splitter = HybridChunker(
                tokenizer=self.tokenizer,
                max_tokens=chunk_size,
                overlap_tokens=chunk_overlap
            )
        else:
            self.tokenizer = None
            self.splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function=len,
                separators=["\n\n", "\n", ". ", " ", ""],
                is_separator_regex=False,
            )

    def chunk_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Chunk text into smaller segments with metadata.

        Args:
            text: Text to chunk
            metadata: Optional metadata to preserve in chunks

        Returns:
            List of dictionaries with 'text' and 'metadata' keys
        """
        start_time = time.time()

        if not text:
            return []

        # Split text into chunks
        text_chunks = self.splitter.split_text(text)

        duration = time.time() - start_time
        logger.info(
            f"Chunked text into {len(text_chunks)} chunks",
            extra={'extra_data': {
                'text_length': len(text),
                'chunk_count': len(text_chunks),
                'chunker_type': self.chunker_type,
                'chunking_duration': round(duration, 3),
            }}
        )

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
