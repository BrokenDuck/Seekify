from __future__ import annotations
import math
from typing import Optional, Union
from flask import current_app, flash, redirect, render_template, request, url_for
from sqlalchemy import func, select
from sqlalchemy.orm import Session, with_parent
from app.parser import get_parser
from app import db
from app.models import Document, TitleTerm, BodyTerm, TitlePostingList, BodyPostingList, TitleCountList, BodyCountList
import heapq

class Result:
    def __init__(self, score: int) -> None:
        self.doc: Optional[Document] = None
        self.score = score

    def populate(self) -> Result:
        self.title = self.doc.title
        self.url = self.doc.url
        self.metadata = f'{str(self.doc.last_modified)} {self.doc.size}'
        self.keywords = ": ".join([\
            f'{word} {count}'\
            for word, count in db.session.execute(\
                select(BodyTerm.word, BodyCountList.count)\
                .where(BodyCountList.doc_id == self.doc.id)\
                .join(BodyTerm, BodyCountList.term)\
                .order_by(BodyCountList.count.desc())\
                .limit(5)\
            ).all()\
        ])
        self.children = [f'{child.title} {child.url}' for child in self.doc.children][0:4]
    
    def __eq__(self, other: Result) -> bool:
        return self.score == other.score
    
    def __lt__(self, other: Result) -> bool:
        return self.score < other.score
    
    def __le__(self, other: Result) -> bool:
        return self.score <= other.score

    def __gt__(self, other: Result) -> bool:
        return self.score > other.score
    
    def __ge__(self, other: Result) -> bool:
        return self.score >= other.score

class Phrase:
    def __init__(self, phrase: list[Union[TitleTerm, BodyTerm]], next_doc: Document) -> None:
        self.phrase = phrase
        self.next_doc = next_doc
    
    def __eq__(self, other: Phrase) -> bool:
        if self.next_doc == None: return False
        return self.next_doc.id == other.next_doc.id

    def __lt__(self, other: Phrase) -> bool:
        if self.next_doc == None: return True
        return self.next_doc.id < other.next_doc.id
    
    def __le__(self, other: Phrase) -> bool:
        if self.next_doc == None: return True
        return self.next_doc.id <= other.next_doc.id
    
    def __gt__(self, other: Phrase) -> bool:
        if self.next_doc == None: return False
        return self.next_doc.id > other.next_doc.id
    
    def __ge__(self, other: Phrase) -> bool:
        if self.nextDoc == None: return False
        return self.next_doc.id >= other.next_doc.id

def prevTitleTerm(db: Session, term: TitleTerm, position: Optional[TitlePostingList]) -> Optional[TitlePostingList]:
    if position is None:
        return None
    return db.scalars(\
        select(TitlePostingList)\
        .where(TitlePostingList.term_id == term.id)\
        .where((TitlePostingList.doc_id <= position.doc_id) & (TitlePostingList.position < position.position))\
        .order_by(TitlePostingList.doc_id.desc())\
    ).first()

def nextTitleTerm(db: Session, term: TitleTerm, position: Optional[TitlePostingList]) -> Optional[TitlePostingList]:
    if position is None:
        return None
    return db.scalars(\
        select(TitlePostingList)\
        .where(TitlePostingList.term_id == term.id)\
        .where((TitlePostingList.doc_id >= position.doc_id) & (TitlePostingList.position > position.position))\
        .order_by(TitlePostingList.doc_id.asc())\
    ).first()

def nextTitlePhrase(db: Session, phrase: list[TitleTerm], position: Optional[TitlePostingList]) -> tuple[Optional[TitlePostingList], Optional[TitlePostingList]]:
    if position is None:
        return None, None
    if len(phrase) == 1:
        u = nextTitleTerm(db, phrase[0], position)
        return u, u
    v = position
    for term in phrase:
        v = nextTitleTerm(db, term, v)
    if v is None:
        return None, None
    u = v
    for term in phrase.reverse():
        u = prevTitleTerm(db, term, u)
    if v.id - u.id == len(phrase) - 1:
        return u, v
    else:
        return nextTitlePhrase(db, phrase, u)

def nextTitleDoc(db: Session, phrase: list[TitleTerm], doc: Optional[Document]) -> Optional[Document]:
    if doc is None:
        doc = db.scalars(\
            select(Document)\
            .order_by(Document.id.asc())\
        ).first()
        if len(phrase) == 1:
            return db.scalars(\
                select(Document)\
                .join(TitleCountList, Document.title_counts)
                .where((TitleCountList.term_id == phrase[0].id) & (TitleCountList.doc_id > doc.id-1))\
                .order_by(Document.id.asc())\
            ).first()
    if len(phrase) == 1:
        return db.scalars(\
            select(Document)\
            .join(TitleCountList, Document.title_counts)
            .where((TitleCountList.term_id == phrase[0].id) & (TitleCountList.doc_id > doc.id))\
            .order_by(Document.id.asc())\
        ).first()
    start, end = nextTitlePhrase(db, phrase, doc.title_postings[0])
    while start is not None and start.document == doc:
        start, end = nextTitlePhrase(db, phrase, end)
    if start is None:
        return None
    return start.document

def title_ftd(db: Session, phrase: list[TitleTerm], doc: Document) -> int:
    if len(phrase) == 1:
        return db.scalar(\
            select(TitleCountList.count)\
            .where((TitleCountList.term_id == phrase[0].id) & (TitleCountList.doc_id == phrase[0].id))\
        )
    count = 0
    start, end = nextTitlePhrase(db, phrase, doc.title_postings[0])
    while start is not None and start.document == doc:
        start, end = nextTitlePhrase(db, phrase, end)
        count += 1
    return count

def title_Nt(db: Session, phrase: list[TitleTerm]) -> int:
    count = 0
    if len(phrase) == 1:
        return db.scalar(\
            select(func.count(TitleCountList.doc_id))\
            .where(TitleCountList.term_id == phrase[0].id)\
        )
    doc = db.scalars(
        select(Document)\
        .order_by(Document.id.asc())\
    ).first()
    while doc is not None:
        doc = nextTitleDoc(db, phrase, doc)
        count += 1
    return count

def prevBodyTerm(db: Session, term: BodyTerm, position: Optional[BodyPostingList]) -> Optional[BodyPostingList]:
    if position is None:
        return None
    return db.scalars(\
        select(BodyPostingList)\
        .where(BodyPostingList.term_id == term.id)\
        .where((BodyPostingList.doc_id <= position.doc_id) & (BodyPostingList.position < position.position))\
        .order_by(BodyPostingList.doc_id.desc())\
    ).first()

def nextBodyTerm(db: Session, term: BodyTerm, position: Optional[BodyPostingList]) -> Optional[BodyPostingList]:
    if position is None:
        return None
    return db.scalars(\
        select(BodyPostingList)\
        .where(BodyPostingList.term_id == term.id)\
        .where((BodyPostingList.doc_id >= position.doc_id) & (BodyPostingList.position > position.position))\
        .order_by(BodyPostingList.doc_id.asc())\
    ).first()

def nextBodyPhrase(db: Session, phrase: list[BodyTerm], position: Optional[BodyPostingList]) -> tuple[Optional[BodyPostingList], Optional[BodyPostingList]]:
    if position is None:
        return None, None
    if len(phrase) == 1:
        u = nextBodyTerm(db, phrase[0], position)
        return u, u
    v = position
    for term in phrase:
        v = nextBodyTerm(db, term, v)
    if v is None:
        return None, None
    u = v
    for term in phrase.reverse():
        u = prevBodyTerm(db, term, u)
    if v.id - u.id == len(phrase) - 1:
        return u, v
    else:
        return nextBodyPhrase(db, phrase, u)

def nextBodyDoc(db: Session, phrase: list[BodyTerm], doc: Document) -> Optional[Document]:
    if doc is None:
        doc = db.scalars(\
            select(Document)\
            .order_by(Document.id.asc())\
        ).first()
        if len(phrase) == 1:
            return db.scalars(\
                select(Document)\
                .join(BodyCountList, Document.body_counts)
                .where((BodyCountList.term_id == phrase[0].id) & (BodyCountList.doc_id > doc.id-1))\
                .order_by(Document.id.asc())\
            ).first()
    if len(phrase) == 1:
        return db.scalars(\
            select(Document)\
            .join(BodyCountList, Document.body_counts)
            .where((BodyCountList.term_id == phrase[0].id) & (BodyCountList.doc_id > doc.id))\
            .order_by(Document.id.asc())\
        ).first()
    start, end = nextBodyPhrase(db, phrase, doc.body_postings[0])
    while start is not None and start.document == doc:
        start, end = nextBodyPhrase(db, phrase, end)
    if start is None:
        return None
    return start.document

def body_ftd(db: Session, phrase: list[BodyTerm], doc: Document) -> int:
    count = 0
    if len(phrase) == 1:
        return db.scalar(\
            select(BodyCountList.count)\
            .where((BodyCountList.term_id == phrase[0].id) & (BodyCountList.doc_id == doc.id))
        )
    start, end = nextBodyPhrase(db, phrase, doc.body_postings[0])
    while start is not None and start.document == doc:
        start, end = nextBodyPhrase(db, phrase, end)
        count += 1
    return count

def body_Nt(db: Session, phrase: list[BodyTerm]) -> int:
    count = 0
    if len(phrase) == 1:
        return db.scalar(\
            select(func.count(BodyCountList.doc_id))\
            .where(BodyCountList.term_id == phrase[0].id)\
        )
    doc = db.scalars(\
        select(Document)\
        .order_by(Document.id.asc())\
    ).first()
    while doc is not None:
        doc = nextBodyDoc(db, phrase, doc)
        count += 1
    return count

def search_db(query: str, top: int = 50) -> list[Document]:
    parser = get_parser()
    phrases = parser.parse_query(query)
    db_session = db.session

    k1 = 1.6
    k2 = 1.2
    b = 0.75
    N: int = db_session.scalar(\
        select(func.count())\
        .select_from(Document)\
    )
    lavg: float = float(db_session.scalar(\
        select(func.avg(Document.size))\
        .select_from(Document)\
    ))

    results = [Result(0) for _ in range(top)]
    
    title_phrases: list[Phrase] = []
    body_phrases: list[Phrase] = []
    for phrase in phrases:
        title_terms = []
        body_terms = []
        for token in phrase:
            title_term = db_session.scalars(\
                select(TitleTerm)\
                .where(TitleTerm.word == token)\
            ).first()
            if title_term is not None:
                title_terms.append(title_term)
            body_term = db_session.scalars(\
                select(BodyTerm)\
                .where(BodyTerm.word == token)\
            ).first()
            if body_term is not None:
                body_terms.append(body_term)
        print(title_terms)
        print(body_terms)
        title_phrases.append(Phrase(title_terms, nextTitleDoc(db_session, title_terms, None)))
        body_phrases.append(Phrase(body_terms, nextBodyDoc(db_session, body_terms, None)))

    heapq.heapify(title_phrases)
    heapq.heapify(body_phrases)

    while title_phrases[0].next_doc is not None or body_phrases[0].next_doc is not None:
        title_doc = title_phrases[0].next_doc
        body_doc = body_phrases[0].next_doc

        print("title")

        score = 0
        while title_doc is not None and (body_doc is None or title_doc.id <= body_doc.id) and title_phrases[0].next_doc == title_doc:
            phrase = title_phrases[0].phrase
            print(phrase)

            # Get the number of times the phrase is present in the title
            Nt = title_Nt(db_session, phrase)
            ftd = title_ftd(db_session, phrase, title_doc)
            score += math.log(N/Nt)*(ftd*(k1+1))/(ftd+k1*((1-b)+b*(title_doc.size/lavg)))
            title_phrases[0].next_doc = nextTitleDoc(db_session, phrase, title_doc)
            title_phrases.sort()
        
        while body_doc is not None and (title_doc is None or body_doc.id <= title_doc.id) and body_phrases[0].next_doc == body_doc:
            phrase = body_phrases[0].phrase
            print(phrase)

            # Get the number of times the phrase is present in the documents
            Nt = body_Nt(db_session, phrase)
            ftd = body_ftd(db_session, phrase, body_doc)
            score += math.log(N/Nt)*(ftd*(k2+1))/(ftd+k2*((1-b)+b*(body_doc.size/lavg)))
            body_phrases[0].next_doc = nextBodyDoc(db_session, phrase, body_doc)
            body_phrases.sort()

        if score > results[0].score:
            res = Result(score)
            if title_doc is not None and title_doc.id <= body_doc.id:
                res.doc = title_doc
            else:
                res.doc = body_doc
            heapq.heappushpop(results, res)
    
    res = []
    for result in results:
        if result.doc is not None and result.score != 0:
            result.populate()
            res.append(result)
    res.sort(reverse=True)
    return res