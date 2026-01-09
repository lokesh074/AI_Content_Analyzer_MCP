from pathlib import Path
from typing import Union
import pypdf


def extract_text_from_pdf(
    pdf_path: str,
    page_numbers: Union[str, list[int]] = "all"
) -> str:
    """
    Extracts text from a PDF file.

    Args:
        pdf_path (str): Path to the PDF file
        page_numbers (str | list[int]): "all" or list of page numbers (1-based)

    Returns:
        str: Extracted text or error message
    """
    status = False
    pdf_file = Path(pdf_path)

    if not pdf_file.exists():
        return f"Error: PDF file not found at {pdf_path}",status

    try:
        reader = pypdf.PdfReader(pdf_file)
        status=True
        # Determine pages to extract
        if page_numbers == "all":
            pages = range(len(reader.pages))
        elif isinstance(page_numbers, list):
            pages = [p - 1 for p in page_numbers]
        else:
            pages = [int(p.strip()) - 1 for p in page_numbers.split(",")]

        extracted_text = ""

        for page_num in pages:
            if 0 <= page_num < len(reader.pages):
                page_text = reader.pages[page_num].extract_text()
                if page_text:
                    extracted_text += f"--- Page {page_num + 1} ---\n"
                    extracted_text += page_text + "\n\n"

        return extracted_text.strip() if extracted_text else "No text extracted.",status

    except Exception as e:
        status=False
        return f"Error while extracting PDF text: {e}",status
