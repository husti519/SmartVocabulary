import re
import csv
import os
from .logger import log_exception

class SmartCSVParser:
    def clean_text(self, text):
        """Cleans whitespace and removes BOM characters, preserving newlines."""
        if not text:
            return ""
        # Remove BOM and other zero-width characters
        text = text.replace('\ufeff', '').replace('\u200b', '')
        # Collapse multiple spaces but keep newlines
        text = re.sub(r'[ \t\f\v]+', ' ', text)
        # Collapse multiple newlines into two at most
        text = re.sub(r'\n\s*\n', '\n\n', text)
        return text.strip()

    def reformat_definition(self, text):
        r"""
        Applies advanced reformatting rules:
        1. Newline before '#' and 'number. ' (except at start).
        2. No newline between 'number. ' and following Korean text.
        3. Remove backslashes from 'number\. '.
        4. Newline before English examples and Korean translations.
        5. Format "#Korean English 1. Korean" as:
           #Korean English
           1. Korean
        """
        if not text:
            return ""
        
        # 3. Strip backslashes from "number\. " early
        text = re.sub(r'(\d+)\\(\.)', r'\1.', text)
        
        # 4. English example (Korean translation) splitting
        # Newline before English example
        text = re.sub(r'([가-힣\s,!\?]{2,})\s*(\([a-zA-Z0-9\s,\.\'\"\-?!]{3,}\))', r'\1\n\2', text)
        text = re.sub(r'([가-힣\s,!\?]{2,})\s+([a-zA-Z]{3,}[a-zA-Z0-9\s,\.\'\"\-]*[\.\!\?])', r'\1\n\2', text)
        
        # Newline before Korean translation
        text = re.sub(r'(\([a-zA-Z0-9\s,\.\'\"\-?!]{3,}\))\s*(\([가-힣\s,!\?]+\))', r'\1\n\2', text)
        text = re.sub(r'([a-zA-Z0-9\s,\.\'\"\-]{3,}[\.\!\?])\s*(\([가-힣\s,!\?]+\))', r'\1\n\2', text)
        text = re.sub(r'([a-zA-Z0-9\s,\.\'\"\-]{3,}[\.\!\?])\s*(?=[가-힣])', r'\1\n', text)

        # 1. Insert newline before "#" and "number. " (if not at start)
        text = re.sub(r'(?<!^)(#)', r'\n\1', text)
        text = re.sub(r'(?<!^)(\d+\.\s)', r'\n\1', text)

        # 2 & 5. Joining back and formatting specific patterns
        # Rule 5 (Updated): Join "#Korean \n English" into "#Korean English"
        # and ensure a newline before "1. "
        text = re.sub(r'(#\s*[가-힣]+)\s*\n+\s*([a-zA-Z]+)', r'\1 \2', text)
        
        # Rule 2: Join "number. " and following Korean text if they were split
        text = re.sub(r'(\d+\.\s)\n+(\(?[가-힣])', r'\1\2', text)

        # Clean up line by line
        lines = [line.strip() for line in text.split('\n')]
        cleaned_lines = [line for line in lines if line]
            
        return '\n'.join(cleaned_lines)

    def parse_line(self, word, definition, apply_reformatting=False):
        """Processes a single word-definition pair with optional advanced reformatting."""
        cleaned_word = self.clean_text(word)
        
        if apply_reformatting:
            processed_def = self.reformat_definition(definition)
        else:
            processed_def = self.clean_text(definition)
        
        return {
            "word": cleaned_word,
            "definition": processed_def
        }

    def import_csv(self, file_path, apply_reformatting=False):
        """Parses a CSV file and returns a list of word-definition dicts."""
        results = []
        if not os.path.exists(file_path):
            return results

        try:
            with open(file_path, mode='r', encoding='utf-8-sig', newline='') as f:
                reader = csv.reader(f)
                
                for row in reader:
                    if len(row) >= 2:
                        word = row[0]
                        # Join all columns from the second onwards as the definition
                        # to handle cases where the definition might contain unquoted commas
                        definition = ",".join(row[1:])
                        
                        parsed_data = self.parse_line(word, definition, apply_reformatting=apply_reformatting)
                        if parsed_data["word"]:
                            results.append(parsed_data)
        except Exception as e:
            log_exception("SmartCSVParser.import_csv", f"Error parsing CSV: {file_path}", e)
        
        return results

if __name__ == "__main__":
    parser = SmartCSVParser()
    test_text = r"1\. (정부의) 권한 #타동사 1\. 지시하다 (mandate a decrease) (인건비 축소를 지시하다.)"
    
    print("--- Default (No Reformatting) ---")
    print(parser.parse_line(" mandate ", test_text, apply_reformatting=False))
    
    print("\n--- With Advanced Reformatting ---")
    res = parser.parse_line(" mandate ", test_text, apply_reformatting=True)
    print(f"Definition:\n{res['definition']}")
