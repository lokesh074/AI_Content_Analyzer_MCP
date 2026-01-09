def chunk_text(
    text: str,
    chunk_size: int = 2000,
    overlap: int = 200
) -> list[str]:
    """
    Splits text into overlapping chunks based on words instead of characters.

    Args:
        text (str): Input text
        chunk_size (int): Number of words per chunk
        overlap (int): Number of overlapping words between chunks

    Returns:
        list[str]: List of text chunks
    """
    words = text.split()
    chunks = []
    start = 0

    while start < len(words):
        end = start + chunk_size
        chunk_words = words[start:end]
        chunks.append(" ".join(chunk_words))
        start = end - overlap

    return chunks
