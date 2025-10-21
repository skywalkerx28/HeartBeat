#!/usr/bin/env python3
import fitz  # PyMuPDF
import sys
import os

def pdf_to_markdown(pdf_path, md_path):
    """Convert PDF to Markdown format"""
    try:
        # Open the PDF
        doc = fitz.open(pdf_path)

        markdown_content = []

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)

            # Extract text
            text = page.get_text()

            # Basic markdown formatting
            lines = text.split('\n')
            formatted_lines = []

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Try to identify headers (simple heuristic)
                if len(line) < 100 and line.isupper():
                    formatted_lines.append(f"# {line}")
                elif len(line) < 80 and line[0].isupper():
                    # Potential subheader
                    formatted_lines.append(f"## {line}")
                else:
                    formatted_lines.append(line)

            # Add page content
            if formatted_lines:
                markdown_content.append("\n".join(formatted_lines))
                markdown_content.append("\n---\n")

        # Write to markdown file
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(markdown_content))

        print(f"Successfully converted {pdf_path} to {md_path}")

    except Exception as e:
        print(f"Error converting PDF: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print(f"Current working directory: {os.getcwd()}")

    # Find the PDF file - look for the three-layer platform document
    pdf_files = [f for f in os.listdir('.') if 'Three-Layer' in f and f.endswith('.pdf')]
    if not pdf_files:
        print("No PDF file found with 'Three-Layer' in the name")
        print("Available PDF files:")
        for f in os.listdir('.'):
            if f.endswith('.pdf'):
                print(f"  {f}")
        sys.exit(1)

    pdf_file = pdf_files[0]
    md_file = "Building_HeartBeat_Three_Layer_Platform.md"

    print(f"Found PDF file: {pdf_file}")
    print(f"Output will be: {md_file}")

    pdf_to_markdown(pdf_file, md_file)
