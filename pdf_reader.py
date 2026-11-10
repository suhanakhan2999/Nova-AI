
from pypdf import PdfReader


def extract_pdf_text(uploaded_file):
    """
    Extract text from an uploaded PDF file.
    """

    try:
        reader = PdfReader(uploaded_file)

        extracted_text = ""

        for page_number, page in enumerate(reader.pages, start=1):

            page_text = page.extract_text()

            if page_text:
                extracted_text += (
                    f"\n--- Page {page_number} ---\n"
                    + page_text
                )

        if not extracted_text.strip():
            return "No readable text found in this PDF."

        return extracted_text

    except Exception as error:
        return f"Error reading PDF: {error}"
