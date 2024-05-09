# For typing
import os
from typing import List, Optional, Union
from __future__ import annotations

# For SQL manipulation
import click
from flask import g
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.db import db_session
from app.models import Document, TitleTerm, BodyTerm, TitleInvertedIndex, BodyInvertedIndex

# For requests
from lxml import html
from urllib.parse import urljoin
import requests

# For text manipulation
import re
from stemmer import PorterStemmer

from collections import deque, Counter
import datetime

class Page:
    def __init__(self, url: str) -> None:
        self.url = url
        self.children = set()
        self.parents = set()
        self.last_modified = None
    
    def set_last_modified(self, last_modified: datetime.datetime) -> None:
        self.last_modified = last_modified

    def add_child(self, child: Page) -> None:
        self.children.add(child)

    def has_child(self, node: Page) -> bool:
        return node in self.children

    def add_parent(self, parent: Page) -> None:
        self.parents.add(parent)

    def has_parent(self, node: Page) -> bool:
        return node in self.parents
    
    def is_older(self, time: datetime.datetime) -> bool:
        if self.last_modified:
            return self.last_modified < time
        else:
            return True
    
    def update(self, last_modified: datetime.datetime, title: str, body: str) -> None:
        self.last_modified = last_modified
        self.title = title
        self.body = body
        self.children = set()
        self.parents = set()

class PageGraph:
    def __init__(self):
        self.pages = set()

    def add_page(self, url: str) -> Page:
        page = Page(url)
        self.pages.add(page)
        return page
    
    def contains(self, url: str) -> Optional[Page]:
        for page in self.pages:
            if page.url == url:
                return page
        return None

class Spider:
    def __init__(self, db: Session, stopword_filepath: str) -> None:
        self.trees = []
        self.crea_time = datetime.datetime.now()
        self.db = db
        self.stemmer = PorterStemmer()
        with open(stopword_filepath, 'r') as f:
            self.words_to_remove = set(word.strip() for word in f.readlines())

    def crawl(self, url: str) -> None:
        graph = PageGraph()
        root = graph.add_page(url)
        to_process = deque()
        to_process.append(root)
        while len(to_process) != 0:
            curr_node = to_process.popleft()

            # Fetch webpage
            last_modified, urls, title, body = self.extract_data(curr_node)

            # Store data
            self.store_data(curr_node.url, title, body)
            
            # Check that the node has not been modified or is a new node
            if curr_node.is_older(last_modified):
                curr_node.update(last_modified, title, body)
            
                # Add links
                for url in urls:
                    res = graph.contains(url)
                    if res:
                        # The child already exists
                        curr_node.add_child(res)
                        res.add_parent(curr_node)
                    else:
                        res = graph.add_page(url)
                        curr_node.add_child(res)
                        res.add_parent(curr_node)
                    # Add res to list of node to process
                    if not res in to_process:
                        to_process.append(res)

    def store_data(self, url: str, title: str, body: str) -> None:
        title_terms = self.extract_terms(title)
        body_terms = self.extract_terms(body)

        try:
            doc = Document(url, title, body)
            db_session.add(doc)
            for title_term, count in title_terms:
                t_term = TitleTerm(title_term)
                db_session.add(t_term)
                db_session.add(TitleInvertedIndex(t_term.term_id, doc.doc_id, count))
            for body_term, count in body_terms:
                b_term = BodyTerm(body_term)
                db_session.add(b_term)
                db_session.add(BodyInvertedIndex(b_term.term_id, doc.doc_id, count))
            db_session.commit()
        except IntegrityError as e:
            # Handle the integrity error
            print("An integrity error occurred:", e)
            # Perform error handling or rollback operations here

    def extract_terms(self, input_string: str) -> Counter[str]:
        # Split the input string into words
        words = re.findall(r'\b\w+\b', input_string)

        # Remove words from the string if they are present in the set of words to remove
        filtered_words = Counter(self.stemmer.stem(word, 0, len(word)-1) for word in words if word.isAlpha() and word not in self.words_to_remove)

        return filtered_words

    def extract_data(self, node: Page) -> Union[datetime.datetime, List[str], str, str]:
        response = requests.get(node.url)
        if response.status_code != 200:
            print(f"Failed to fetch the webpage: {node.url}, {response.status_code}")
            return None, None, None, None
        
        # Parse webpage
        tree = html.fromstring(response.content)
        # Attempt to grab the last modified time
        last_modified_element = tree.xpath('//meta[@http-equiv="Last-Modified"]/@content')
        if last_modified_element:
            # Assuming last modification time is in a standard format like ISO 8601
            last_modified_time = datetime.datetime.strptime(last_modified_element[0], "%a, %d %b %Y %H:%M:%S %Z")
        else:
            # If we were unable to grab the last modified time we set it to the current time
            print("Last modification time not found")
            last_modified_time = self.crea_time
        # Grab children links
        links = map(lambda s: urljoin(node.url, s), tree.xpath('//a/@href'))
        # Attemp to grab the title
        title_element = tree.find(".//title")
        if title_element is not None:
            title = title_element.text
        else:
            print("Title element not found")
            title = "No title"
        # Extract the body element
        body_element = tree.find(".//body")
        if body_element is not None:
            # Serialize the body element to get its inner HTML content
            body = html.tostring(body_element, encoding='windows-1252')
        else:
            print("Body element not found")
            body = "No body"
        return last_modified_time, list(links), title, body
    
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