#!/usr/bin/env python3
"""
Script to extract metadata from PDF files in data/raw directory
and generate a markdown table for fuentes.md
"""

import os
import re
from pathlib import Path
from PyPDF2 import PdfReader

def extract_pdf_metadata(pdf_path):
    """Extract metadata from a PDF file."""
    try:
        reader = PdfReader(pdf_path)
        metadata = reader.metadata

        # Initialize default values
        url = ''
        date = ''
        version = ''

        if metadata:
            # Try to get URL from metadata
            if '/URI' in metadata:
                url = str(metadata['URI'])
            # Try to get date from metadata
            if '/CreationDate' in metadata:
                # PDF date format: D:YYYYMMDDHHmmSSOHH'mm'
                date_str = str(metadata['CreationDate'])
                # Extract YYYY-MM-DD
                date_match = re.search(r'D:(\d{4})(\d{2})(\d{2})', date_str)
                if date_match:
                    date = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"
            # Try to get version or title
            if '/Title' in metadata:
                title = str(metadata['Title'])
                # Extract version info from title if possible
                if 'consolidado' in title.lower():
                    version = 'consolidado'
                elif 'versión' in title.lower() or 'version' in title.lower():
                    # Try to extract version number
                    version_match = re.search(r'[vV]ersión?\s*[:\s]*(\d+(?:\.\d+)*)', title, re.IGNORECASE)
                    if version_match:
                        version = version_match.group(1)

        return url, date, version
    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")
        return '', '', ''

def extract_from_filename(filename):
    """Extract information from filename when PDF metadata is insufficient."""
    name = Path(filename).stem
    url = ''
    date = ''
    version = ''

    # Handle BOE files: BOE-A-YYYY-NNNNN[-more].pdf
    boe_match = re.match(r'BOE-A-(\d{4})-(\d+)', name)
    if boe_match:
        year = boe_match.group(1)
        date = f"{year}-01-01"  # Approximate, could be improved
        # Construct BOE URL
        url = f"https://www.boe.es/diario_boe/txt.php?id=BOE-A-{year}-{boe_match.group(2)}"
        if 'consolidado' in name.lower():
            version = 'consolidado'
        return url, date, version, name

    # Handle CELEX files: CELEX_XXXXXXXXXXXXX_XX_TXT.pdf
    celex_match = re.match(r'CELEX_(\d{4})([A-Z]\d{4})(_[A-Z]{2})?_TXT', name)
    if celex_match:
        year = celex_match.group(1)
        date = f"{year}-01-01"  # Approximate
        # Construct CELEX URL
        celex_id = f"{celex_match.group(1)}{celex_match.group(2)}{celex_match.group(3) or ''}"
        url = f"https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:{celex_id}"
        return url, date, version, name

    # Default: return just the name
    return url, date, version, name

def main():
    raw_dir = Path("c:/ICAI/Proyectos y Prácticas/ENAGAS-IA/LEXIA_GIT/.git/ENAG-S_G1/data/raw")
    output_file = Path("c:/ICAI/Proyectos y Prácticas/ENAGAS-IA/LEXIA_GIT/.git/ENAG-S_G1/data/fuentes.md")

    if not raw_dir.exists():
        print(f"Directory {raw_dir} does not exist")
        return

    # Find all PDF files
    pdf_files = list(raw_dir.glob("*.pdf"))

    if not pdf_files:
        print("No PDF files found in", raw_dir)
        return

    # Prepare markdown table
    lines = [
        "# Fuentes de datos",
        "",
        "| URL | Fecha | Versión | Nombre |",
        "|-----|-------|---------|--------|"
    ]

    for pdf_file in sorted(pdf_files):
        print(f"Processing {pdf_file.name}...")

        # Try to get metadata from PDF
        url, date, version = extract_pdf_metadata(pdf_file)

        # If metadata is insufficient, try filename
        if not url or not date:
            url_from_name, date_from_name, version_from_name, name_from_file = extract_from_filename(pdf_file.name)
            if not url:
                url = url_from_name
            if not date:
                date = date_from_name
            if not version:
                version = version_from_name

        # Clean up name for display
        name = pdf_file.stem
        # Remove file extension if still present
        if name.endswith('.pdf'):
            name = name[:-4]

        # Format date if we have a partial date
        if date and date.endswith('-01-01'):
            # Try to get better date from filename patterns
            if 'BOE-A-' in name:
                # Extract year from BOE-A-YYYY-NNNN
                year_match = re.search(r'BOE-A-(\d{4})', name)
                if year_match:
                    date = f"{year_match.group(1)}-01-01"  # Still approximate
            elif 'CELEX_' in name and '_' in name:
                # Extract year from CELEX_YYYY...
                year_match = re.search(r'CELEX_(\d{4})', name)
                if year_match:
                    date = f"{year_match.group(1)}-01-01"

        lines.append(f"| {url} | {date} | {version} | {name} |")

    # Write to file
    output_file.write_text('\n'.join(lines), encoding='utf-8')
    print(f"Metadata extracted and saved to {output_file}")
    print(f"Processed {len(pdf_files)} PDF files.")

if __name__ == "__main__":
    main()