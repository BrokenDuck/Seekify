from nltk.stem.porter import *
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords

from collections import Counter

class Parser:
    def __init__(self) -> None:
        self.stemmer = PorterStemmer()
        self.stopwords = set(stopwords.words('english'))
    
    def parse(self, content: str) -> Counter:
        # Tokenize the text content of the webpage
        tokens = word_tokenize(content)

        # Filter out the stopwords
        filtered_tokens = [word for word in tokens if word.lower() not in self.stopwords]

        # Stem the token using the PorterStemmer
        stemmed_tokens = map(lambda w: self.stemmer.stem(w, 0, len(w)-1), filtered_tokens)

        # Stemmed tokens counter
        tokens_counter = Counter(stemmed_tokens)

        return tokens_counter

