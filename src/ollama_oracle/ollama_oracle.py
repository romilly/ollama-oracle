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

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5")

class Librarian:

    def __init__(self):
        self.connection = sqlite3.connect('../../pdf_files.db')
        self._create_table()
        self.client = Client(host=OLLAMA_URL)
        print(OLLAMA_URL)

    def __del__(self):
        self.connection.close()

    def find_paper(self, path: str) -> Paper:
        text = extract_text(path, maxpages=1)
        messages = [{
            "role": "user",
            "content": TEMPLATE.format(text=text)
        }]
        response = self.client.chat(OLLAMA_MODEL, messages=messages, format=PAPER_FORMAT)
        return Paper.model_validate_json(response.message.content)


    def update_paper(self, path: str):
        paper = self.find_paper(path)
        sql = """
        INSERT OR REPLACE INTO pdf_info (path, title, authors)
        VALUES (?, ?, ?)

        """
        cursor = self.connection.cursor()
        params = (path, paper.title, ', '.join(paper.authors))
        print(params)
        cursor.execute(sql, params)
        self.connection.commit()

    def _create_table(self):
        """Create the pdf_info table if it does not exist."""
        create_table_query = """
        CREATE TABLE IF NOT EXISTS pdf_info (
            path TEXT PRIMARY KEY,
            title TEXT,
            authors TEXT,
            UNIQUE(title)
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
    load_dotenv()
    DIRECTORY = os.getenv("DIRECTORY", "../data/pdfs")
    start_time = time.time()
    # files = pdfs_in('../../data/pdfs')
    files = pdfs_in(DIRECTORY)
    print(len(files))
    library = Librarian()
    library.process_files(*files)
    end_time = time.time()
    print(f"\nTime taken: {end_time - start_time:.2f} seconds")
