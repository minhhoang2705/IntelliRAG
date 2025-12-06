"""Utility functions for IntelliRAG."""


def extract_file_extension(file_path: str) -> str:
    """Extract file extension from file path.
    
    Args:
        file_path: Path to file (can be local path or GCS URI)
        
    Returns:
        Lowercase file extension without dot, or 'unknown' if no extension
        
    Examples:
        >>> extract_file_extension("document.pdf")
        'pdf'
        >>> extract_file_extension("gs://bucket/file.PDF")
        'pdf'
        >>> extract_file_extension("no_extension")
        'unknown'
    """
    if '.' in file_path:
        return file_path.split('.')[-1].lower()
    return 'unknown'
