from typing import Optional, List
from sqlalchemy import Column, ForeignKey, Integer, String, Table, Time
from sqlalchemy.orm import relationship, mapped_column, Mapped
from app.db import Base

"""Contains the SQL Schema definitions"""

document_to_document = Table(
    "document_to_document",
    Base.metadata,
    Column("left_doc_id", Integer, ForeignKey("documents.doc_id"), primary_key=True),
    Column("right_doc_id", Integer, ForeignKey("documents.doc_id"), primary_key=True)
)

class Document(Base):
    __tablename__ = 'documents'

    doc_id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    
    last_modified: Mapped[Time]
    size: Mapped[int]
    title: Mapped[Optional[str]] = mapped_column(String(255))
    content: Mapped[Optional[str]]

    title_terms: Mapped[List["TitleTerm"]] = relationship("TitleInvertedIndex", back_populates="document") # To generate forward index
    body_terms: Mapped[List["BodyTerm"]] = relationship("BodyInvertedIndex", back_populates="document") # To generate forward index

    parents: Mapped[List["Document"]] = relationship(
        "Document",
        secondary=document_to_document,
        primaryjoin=doc_id == document_to_document.c.left_doc_id,
        secondaryjoin=doc_id == document_to_document.c.right_doc_id,
        back_populates="children"
    )
    children: Mapped[List["Document"]] = relationship(
        "Document",
        secondary=document_to_document,
        primaryjoin=id == document_to_document.c.right_doc_id,
        secondaryjoin=id == document_to_document.c.left_doc_id,
        back_populates="parents"
    )
    
    def __repr__(self) -> str:
        return f'<Document {self.url!r} {self.title!r}>'

class TitleTerm(Base):
    __tablename__ = "title_terms"

    term_id: Mapped[int] = mapped_column(primary_key=True)
    word: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)

    entries: Mapped[List["TitleInvertedIndex"]] = relationship("TitleInvertedIndex", back_populates="title_term")

    def __repr__(self) -> str:
        return f'<TitleTerm {self.word!r}>'

class BodyTerm(Base):
    __tablename__ = "body_terms"

    term_id: Mapped[int] = mapped_column(primary_key=True)
    word: Mapped[str] = mapped_column(unique=True, index=True)
    
    entries: Mapped[List["BodyInvertedIndex"]] = relationship("BodyInvertedIndex", back_populates="body_term")

    def __repr__(self) -> str:
        return f'<TitleTerm {self.word!r}>'

class TitleInvertedIndex(Base):
    __tablename__ = 'title_inverted_index'

    entry_id: Mapped[int] = mapped_column(primary_key=True)

    document: Mapped["Document"] = relationship("Document", back_populates="title_terms") # To generate forward index
    term: Mapped["TitleTerm"] = relationship("TitleTerm", back_populates="entries")

    frequency: Mapped[int]
    
    def __repr__(self) -> str:
        return f'<TitleInvertedIndex {self.term.word!r} {self.document.url!r} {self.frequency!r}>'

class BodyInvertedIndex(Base):
    __tablename__ = 'body_inverted_index'

    entry_id: Mapped[int] = mapped_column(primary_key=True)

    document: Mapped["Document"] = relationship("Document", back_populates="body_terms") # To generate forward index
    term: Mapped["BodyTerm"] = relationship("BodyTerm", back_populates="entries")

    frequency: Mapped[int]
    
    def __repr__(self) -> str:
        return f'<BodyInvertedIndex {self.term.word!r} {self.document.url!r} {self.frequency!r}>'