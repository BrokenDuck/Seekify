from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.db import Base

"""Contains the SQL Schema defintions"""

class Document(Base):
    __tablename__ = 'documents'

    doc_id = Column(Integer, primary_key=True)
    url = Column(String(255), unique=True, index=True, nullable=False)
    title = Column(String(255))
    content = Column(String)

    title_terms = relationship("TitleInvertedIndex", back_populates="document") # To generate forward index
    body_terms = relationship("BodyInvertedIndex", back_populates="document") # To generate forward index

    def __init__(self, url: str, title: str = None, content: str = None) -> None:
        self.url = url
        self.title = title
        self.content = content
    
    def __repr__(self) -> str:
        return f'<Document {self.url!r} {self.title!r}>'

class TitleTerm(Base):
    __tablename__ = "title_terms"

    term_id = Column(Integer, primary_key=True)
    word = Column(String, unique=True, index=True, nullable=False)

    def __init__(self, word: str) -> None:
        self.word = word
    
    def __repr__(self) -> str:
        return f'<TitleTerm {self.word!r}>'

class BodyTerm(Base):
    __tablename__ = "body_terms"

    term_id = Column(Integer, primary_key=True)
    word = Column(String, unique=True, index=True)

    def __init__(self, word: str) -> None:
        self.word = word
    
    def __repr__(self) -> str:
        return f'<TitleTerm {self.word!r}>'

class TitleInvertedIndex(Base):
    __tablename__ = 'title_inverted_index'

    entry_id = Column(Integer, primary_key=True)
    term_id = Column(Integer, ForeignKey('title_terms.term_id'))
    doc_id = Column(Integer, ForeignKey('documents.doc_id'))
    frequency = Column(Integer)

    document = relationship("Document", back_populates="title_terms") # To generate forward index

    def __init__(self, term_id: int, doc_id: int, frequency: int = None) -> None:
        self.term_id = term_id
        self.doc_id = doc_id
        self.frequency = frequency
    
    def __repr__(self) -> str:
        return f'<TitleInvertedIndex {self.term_id!r} {self.doc_id!r} {self.frequency!r}>'

class BodyInvertedIndex(Base):
    __tablename__ = 'body_inverted_index'

    entry_id = Column(Integer, primary_key=True)
    term_id = Column(Integer, ForeignKey('body_terms.term_id'))
    doc_id = Column(Integer, ForeignKey('documents.doc_id'))
    frequency = Column(Integer)

    document = relationship("Document", back_populates="body_terms") # To generate forward index

    def __init__(self, term_id: int, doc_id: int, frequency: int = None) -> None:
        self.term_id = term_id
        self.doc_id = doc_id
        self.frequency = frequency
    
    def __repr__(self) -> str:
        return f'<BodyInvertedIndex {self.term_id!r} {self.doc_id!r} {self.frequency!r}>'