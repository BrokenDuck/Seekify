from typing import Optional, List
from sqlalchemy import Column, ForeignKey, Integer, String, Table, Time
from sqlalchemy.orm import relationship, mapped_column, Mapped
from app.db import Base

"""Contains the SQL Schema definitions"""

document_to_document = Table(
    "document_to_document",
    Base.metadata,
    Column("left_id", Integer, ForeignKey("documents.doc_id"), primary_key=True),
    Column("right_id", Integer, ForeignKey("documents.doc_id"), primary_key=True)
)

class Document(Base):
    __tablename__ = 'document_table'

    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    
    last_modified: Mapped[Time]
    size: Mapped[int]
    title: Mapped[Optional[str]] = mapped_column(String(255))
    content: Mapped[Optional[str]]

    title_postings: Mapped[List["TitlePostingList"]] = relationship("TitlePostingList", back_populates="document") # To generate forward index
    title_counts: Mapped[List["TitleCountList"]] = relationship("TitleCountList", back_populates="document") # To generate forward index
    body_postings: Mapped[List["BodyPostingList"]] = relationship("BodyPostingList", back_populates="document") # To generate forward index
    body_counts: Mapped[List["BodyCountList"]] = relationship("BodyCountList", back_populates="document") # To generate forward index

    parents: Mapped[List["Document"]] = relationship(
        "Document",
        secondary=document_to_document,
        primaryjoin=id == document_to_document.c.left_id,
        secondaryjoin=id == document_to_document.c.right_id,
        back_populates="children"
    )
    children: Mapped[List["Document"]] = relationship(
        "Document",
        secondary=document_to_document,
        primaryjoin=id == document_to_document.c.right_id,
        secondaryjoin=id == document_to_document.c.left_id,
        back_populates="parents"
    )
    
    def __repr__(self) -> str:
        return f'<Document {self.url!r} {self.title!r}>'

class TitleTerm(Base):
    __tablename__ = "title_term_table"

    id: Mapped[int] = mapped_column(primary_key=True)
    word: Mapped[str] = mapped_column(unique=True, index=True)

    postings: Mapped[List["TitlePostingList"]] = relationship("TitlePostingList", back_populates="term")
    counts: Mapped[List["TitleCountList"]] = relationship("TitleCountList", back_populates="term")

    def __repr__(self) -> str:
        return f'<TitleTerm {self.word!r}>'

class BodyTerm(Base):
    __tablename__ = "body_term_table"

    id: Mapped[int] = mapped_column(primary_key=True)
    word: Mapped[str] = mapped_column(unique=True, index=True)
    
    postings: Mapped[List["BodyPostingList"]] = relationship("BodyPostingList", back_populates="term")
    counts: Mapped[List["BodyCountList"]] = relationship("BodyCountList", back_populates="term")

    def __repr__(self) -> str:
        return f'<TitleTerm {self.word!r}>'

class TitlePostingList(Base):
    __tablename__ = 'title_posting_table'

    id: Mapped[int] = mapped_column(primary_key=True)

    doc_id: Mapped[int] = mapped_column(ForeignKey("document_table.id"))
    document: Mapped["Document"] = relationship("Document", back_populates="title_postings") # To generate forward index
    term_id: Mapped[int] = mapped_column(ForeignKey("title_term_table.id"))
    term: Mapped["TitleTerm"] = relationship("TitleTerm", back_populates="postings") # To generate dictionary

    position: Mapped[int]
    
    def __repr__(self) -> str:
        return f'<TitlePostingList {self.term!r} {self.document!r} {self.frequency!r}>'

class TitleCountList(Base):
    __tablename__ = 'title_count_table'

    id: Mapped[int] = mapped_column(primary_key=True)

    doc_id: Mapped[int] = mapped_column(ForeignKey("document_table.id"))
    document: Mapped["Document"] = relationship("Document", back_populates="title_counts") # To generate forward index
    term_id: Mapped[int] = mapped_column(ForeignKey("title_term.id"))
    term: Mapped["TitleTerm"] = relationship("TitleTerm", back_populates="counts") # To generate dictionary

    count: Mapped[int]

    def __repr__(self) -> str:
        return f'<TitleCountList {self.term!r} {self.document!r} {self.count}'

class BodyPostingList(Base):
    __tablename__ = 'body_posting_list'

    id: Mapped[int] = mapped_column(primary_key=True)

    doc_id: Mapped[int] = mapped_column(ForeignKey("document_table.id"))
    document: Mapped["Document"] = relationship("Document", back_populates="body_postings") # To generate forward index
    term_id: Mapped[int] = mapped_column(ForeignKey("body_term.id"))
    term: Mapped["BodyTerm"] = relationship("BodyTerm", back_populates="postings") # To generate dictionary

    position: Mapped[int]
    
    def __repr__(self) -> str:
        return f'<BodyInvertedIndex {self.term!r} {self.document!r} {self.frequency!r}>'
    
class BodyCountList(Base):
    __tablename__ = 'title_count_table'

    id: Mapped[int] = mapped_column(primary_key=True)

    doc_id: Mapped[int] = mapped_column(ForeignKey("document_table.id"))
    document: Mapped["Document"] = relationship("Document", back_populates="body_counts") # To generate forward index
    term_id: Mapped[int] = mapped_column(ForeignKey("body_term.id"))
    term: Mapped["TitleTerm"] = relationship("BodyTerm", back_populates="counts") # To generate dictionary

    count: Mapped[int]

    def __repr__(self) -> str:
        return f'<BodyCountList {self.term!r} {self.document!r} {self.count}'