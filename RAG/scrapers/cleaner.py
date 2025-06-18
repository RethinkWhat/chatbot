import re
import unicodedata
class Cleaner:
    def runOCRCleaner(text: str) -> str:
        # Normalize Unicode (e.g., fancy quotes → straight quotes)
        text = unicodedata.normalize("NFKC", text)

        # Remove decorative or layout artifacts
        text = re.sub(r'[_~^=*•●■▪]+', '', text)        # Remove underlines or bullets
        text = re.sub(r'\|+', ' ', text)                # Replace vertical bars with space
        text = re.sub(r'-{2,}', ' ', text)              # Long dashes (tables, dividers)

        # Fix common spacing issues
        text = re.sub(r' {2,}', ' ', text)              # Collapse multiple spaces
        text = re.sub(r'\n{3,}', '\n\n', text)          # Too many newlines → double newline
        text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)    # Mid-sentence line breaks → space

        # Optional: strip non-ASCII characters (keep this commented if you want multilingual)
        # text = re.sub(r'[^\x00-\x7F]+', '', text)

        # Remove leading/trailing whitespace on each line
        lines = [line.strip() for line in text.splitlines()]
        cleaned = '\n'.join(line for line in lines if line)  # Drop empty lines

        return cleaned.strip()
