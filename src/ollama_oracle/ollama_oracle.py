#!/usr/bin/env python
# coding: utf-8
import os
import time
import sqlite3
from pdfminer.high_level import extract_text
from pydantic import BaseModel
from ollama import Client
from dotenv import load_dotenv

load_dotenv()
TEMPLATE = "Can you tell me the title and author from this start of an academic paper?{text}"


class Paper(BaseModel):
    title: str
    authors: list[str]


PAPER_FORMAT = Paper.model_json_schema()

DIRECTORY = os.getenv("DIRECTORY", "../data/pdfs")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "30"))  # timeout in seconds

class Librarian:

    def __init__(self):
        self.connection = sqlite3.connect('../../pdf_files.db')
        self._create_table()
        self.client = Client(host=OLLAMA_URL)
        print(f"Searching {DIRECTORY} using model {OLLAMA_MODEL} on Ollama server at {OLLAMA_URL}")
        print(f"Timeout set to {OLLAMA_TIMEOUT} seconds")

    def __del__(self):
        self.connection.close()

    def find_paper(self, path: str) -> Paper:
        text = extract_text(path, maxpages=1)
        messages = [{
            "role": "user",
            "content": TEMPLATE.format(text=text)
        }]
        try:
            response = self.client.chat(
                OLLAMA_MODEL, 
                messages=messages, 
                format=PAPER_FORMAT,
                options={"timeout": OLLAMA_TIMEOUT}
            )
            return Paper.model_validate_json(response.message.content)
        except Exception as e:
            if "timeout" in str(e).lower():
                raise Exception(f"Ollama request timed out after {OLLAMA_TIMEOUT} seconds") from e
            raise

    def update_paper(self, path: str):
        sql = """
        INSERT OR REPLACE INTO pdf_info (path, title, authors)
        VALUES (?, ?, ?)

        """

        try:
            paper = self.find_paper(path)
            cursor = self.connection.cursor()
            params = (path, paper.title, ', '.join(paper.authors))
            print(params)
            cursor.execute(sql, params)
            self.connection.commit()
        except Exception as e:
            print(f"Cannot update {path}: {e}")

    def _create_table(self):
        """Create the pdf_info table if it does not exist."""
        create_table_query = """
        CREATE TABLE IF NOT EXISTS pdf_info (
            path TEXT PRIMARY KEY,
            title TEXT,
            authors TEXT
        );
        """
        cursor = self.connection.cursor()
        cursor.execute(create_table_query)
        self.connection.commit()


    def process_files(self, *file_list: str):
        for path in file_list:
            self.update_paper(path.strip())

import os


def pdfs_in(directory: str):
    pdf_files = []
    # Walk through the given directory and subdirectories
    for root, _, files in os.walk(directory):
        for file in files:
            # Check if file has a .pdf extension (case-insensitive)
            if file.lower().endswith('.pdf'):
                # Add the absolute path of the PDF to the list
                pdf_files.append(os.path.abspath(os.path.join(root, file)))
    return pdf_files


if __name__ == '__main__':
    start_time = time.time()
    # files = pdfs_in('../../data/pdfs')
    files = pdfs_in(DIRECTORY)
    print(len(files))
    library = Librarian()
    library.process_files(*files)
    end_time = time.time()
    print(f"\nTime taken: {end_time - start_time:.2f} seconds")
