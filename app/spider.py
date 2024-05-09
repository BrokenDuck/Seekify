# For typing
from typing import Optional
from __future__ import annotations

# For Flask
import os
import click
from flask import g

# For SQL manipulation
from sqlalchemy.orm import Session
from app.db import db_session
from app.models import Document, TitleTerm, BodyTerm, TitleInvertedIndex, BodyInvertedIndex

# For requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import requests

# For text manipulation
from collections import deque
import datetime
from app.parser import Parser

class UniqueQueue:
    def __init__(self):
        self.queue = deque()
        self.unique_set = set()

    def enqueue(self, item):
        if item not in self.unique_set:
            self.queue.append(item)
            self.unique_set.add(item)

    def dequeue(self):
        if self.queue:
            item = self.queue.popleft()
            self.unique_set.remove(item)
            return item
        else:
            raise IndexError("Queue is empty")

    def is_empty(self):
        return len(self.queue) == 0

    def __len__(self):
        return len(self.queue)

class DocumentMap:
    def __init__(self):
        self.documents = {}
    
    def get_document(self, url: str) -> Document:
        if url not in self.documents:
            doc = Document(url=url)
            self.documents[url] = doc
            return doc
        else:
            return self.documents[url]

class TitleTermMap:
    def __init__(self):
        self.title_terms = {}

    def get_title_term(self, word: str) -> TitleTerm:
        if word not in self.title_terms:
            title_term = TitleTerm(word=word)
            self.title_terms[word] = title_term
            return title_term
        else:
            return self.title_terms[word]
        
class BodyTermMap:
    def __init__(self):
        self.body_terms = {}

    def get_body_term(self, word: str) -> BodyTerm:
        if word not in self.body_terms:
            title_term = TitleTerm(word=word)
            self.body_terms[word] = title_term
            return title_term
        else:
            return self.body_terms[word]

class Spider:
    def __init__(self, db: Session) -> None:
        self.creation_time = datetime.datetime.now()
        self.db = db
        self.parser = Parser()
        self.docs = DocumentMap()
        self.title_terms = TitleTermMap()
        self.body_terms = BodyTermMap()

    def crawl(self, url: str) -> None:
        root = self.docs.get_document(url)
        to_process = UniqueQueue()
        to_process.enqueue(root)
        while not to_process.is_empty():
            doc = to_process.dequeue()
            
            # Request webpage
            response = requests.get(doc.url)
            if response.status_code != 200:
                print(f"Failed to fetch the webpage: {doc.url}, {response.status_code}")
                continue
            
            # Parse webpage
            soup = BeautifulSoup(response.text, 'lxml')

            # Attempt to grab the last modified time
            last_modified_tag = soup.find('meta', attrs={'name': 'last-modified'})
            if last_modified_tag is not None:
                # Assuming last modification time is in a standard format like ISO 8601
                last_modified_date = datetime.datetime.strptime(last_modified_tag['content'], "%a, %d %b %Y %H:%M:%S %Z")

                # If the last modified date of the page is not older than the new last modified date, we abort
                if doc.last_modified is not None and doc.last_modified < last_modified_date:
                    continue
                
                doc.last_modified = last_modified_date
            else:
                # If we were unable to grab the last modified time we set it to the current time
                print("Last modification time not found")
                doc.last_modified = self.creation_time

            # Attempt the grab the page size
            size_tag = soup.find('meta', attrs={'name': 'size'})
            if size_tag is not None:
                doc.size = size_tag['content']
            else:
                print("Page size not found")
                doc.size = len(response.text)

            # Attemp to grab the title
            title_tag = soup.find('title')
            if title_tag is not None:
                doc.title = title_tag.text
                for word, count in self.parser.parse(title_tag.text):
                    title_term = self.title_terms.get_title_term(word)
                    TitleInvertedIndex(term=title_term, document=doc, frequency=count)
            else:
                print("Title element not found")
            
            # Extract the body element
            body_tag = soup.body
            if body_tag is not None:
                # Serialize the body element to get its inner HTML content
                doc.content = str(body_tag)
                for word, count in self.parse.parse(doc.body.get_text()):
                    body_term = self.body_terms.get_body_term(word)
                    BodyInvertedIndex(term=body_term, document=doc, frequency=count)

                for url in [urljoin(doc.url, link.get('href')) for link in body_tag.find_all('a')]:
                    child_doc = self.docs.get_document(url)
                    doc.children.append(child_doc)
                    child_doc.parents.append(doc)

            else:
                print("Body element not found")

        for doc in self.docs.documents.values():
            self.db.add(doc)
        
        for title_term in self.title_terms.title_terms.values():
            self.db.add(title_term)
        
        for body_term in self.body_terms.body_terms.values():
            self.db.add(body_term)
        
        self.db.commit()

    
def get_spider() -> Spider:
    if not 'spider' in g:
        g.spider = Spider(db_session, os.path.abspath('./static/stopwords.txt'))
    
    return g.spider

def init_spider():
    spider = get_spider()

    spider.crawl('https://www.cse.ust.hk/~kwtleung/COMP4321/testpage.htm')

@click.command('init-spider')
def init_spider_command():
    """Crawl base website and index it in the database."""
    init_spider()
    click.echo('Initialized spider')

def init_app(app):
    app.teardown_appcontext(close_spider)
    app.cli.add_command(init_spider_command)

def close_spider(e=None):
    g.pop('spider', None)