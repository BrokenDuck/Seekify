from flask import g
from nltk.stem.porter import *
from nltk.tokenize import regexp_tokenize, word_tokenize
from nltk.corpus import stopwords
from collections import Counter

class Parser:
    def __init__(self) -> None:
        self.stemmer = PorterStemmer()
        self.stopwords = set(stopwords.words('english'))
    
    def parse(self, content: str) -> tuple[list[str], Counter]:
        # Tokenize the text content of the webpage
        tokens = word_tokenize(content)

        # Filter out the stopwords
        filtered_tokens = [word for word in tokens if word.lower() not in self.stopwords]

        # Stem the token using the PorterStemmer
        stemmed_tokens = map(lambda w: self.stemmer.stem(w, 0, len(w)-1), filtered_tokens)

        return stemmed_tokens, Counter(stemmed_tokens)
    
    def parse_query(self, content: str) -> list[list[str]]:
        if '"' in content:
            expr = r'\w+|[^\w\s]+|"[^"]*"'
            tokens = [word_tokenize(part) for part in regexp_tokenize(content, expr)]
        else: 
            tokens = word_tokenize(content)
        
        # Filter out the stopwords
        filtered_tokens = [word for word in tokens if word.lower() not in self.stopwords]

        # Stem the token using the PorterStemmer
        stemmed_tokens = map(lambda w: self.stemmer.stem(w, 0, len(w)-1), filtered_tokens)

        return stemmed_tokens



def get_parser() -> Parser:
    if 'parser' not in g:
        g.parser = Parser()
    return g.parser