import math
from typing import Optional, Union
from flask import current_app, flash, render_template, request
from sqlalchemy import func, select
from sqlalchemy.orm import Session, with_parent
from app.parser import get_parser
from app import db
from app.models import Document, TitleTerm, BodyTerm, TitlePostingList, BodyPostingList, TitleCountList, BodyCountList
import heapq
from __future__ import annotations

class Result:
    def __init__(self, score: int) -> None:
        self.doc: Optional[Document] = None
        self.score = score

    def populate(self) -> Result:
        self.title = self.doc.title
        self.url = self.doc.url
        self.metadata = f'{str(self.doc.last_modified)} {self.doc.size}'
        self.keywords = [\
            f'{word} {count}'\
            for word, count in db.scalars(\
                select(BodyTerm.word, BodyCountList.count)\
                .where(with_parent(self.doc, BodyCountList.document))\
                .join(BodyTerm, BodyCountList.term)\
            ).all()\
        ].join('; ')
        self.children = [f'{child.title} {child.url}' for child in self.doc.children]
    
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
        .where(with_parent(term, TitleTerm.postings))\
        .where(TitlePostingList.doc_id <= position.doc_id and TitlePostingList.position < position.position)\
        .order_by(TitlePostingList.doc_id.desc())\
    ).first()

def nextTitleTerm(db: Session, term: TitleTerm, position: Optional[TitlePostingList]) -> Optional[TitlePostingList]:
    if position is None:
        return None
    return db.scalars(\
        select(TitlePostingList)\
        .where(with_parent(term, TitleTerm.postings))\
        .where(TitlePostingList.doc_id >= position.doc_id and TitlePostingList.position > position.position)\
        .order_by(TitlePostingList.doc_id.asc())\
    ).first()

def nextTitlePhrase(db: Session, phrase: list[TitleTerm], position: Optional[TitlePostingList]) -> tuple[Optional[TitlePostingList], Optional[TitlePostingList]]:
    if position is None:
        return None
    if len(phrase) == 1:
        return nextTitleTerm(db, phrase[0], position)
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

def nextTitleDoc(db: Session, phrase: list[TitleTerm], doc: Document) -> Optional[Document]:
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
            .where(with_parent(phrase[0], TitleCountList.term) and with_parent(doc, TitleCountList.document))\
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
            select(func.count())\
            .select_from(\
                select(TitleCountList.document)\
                .where(with_parent(phrase[0], TitleCountList.term))\
            )\
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
        .where(with_parent(term, BodyTerm.postings))\
        .where(BodyPostingList.doc_id <= position.doc_id and BodyPostingList.position < position.position)\
        .order_by(BodyPostingList.doc_id.desc())\
    ).first()

def nextBodyTerm(db: Session, term: BodyTerm, position: Optional[BodyPostingList]) -> Optional[BodyPostingList]:
    if position is None:
        return None
    return db.scalars(\
        select(BodyPostingList)\
        .where(with_parent(term, BodyTerm.postings))\
        .where(BodyPostingList.doc_id >= position.doc_id and BodyPostingList.position > position.position)\
        .order_by(BodyPostingList.doc_id.asc())\
    ).first()

def nextBodyPhrase(db: Session, phrase: list[BodyTerm], position: Optional[BodyPostingList]) -> tuple[Optional[BodyPostingList], Optional[BodyPostingList]]:
    if position is None:
        return None
    if len(phrase) == 1:
        return nextBodyTerm(db, phrase[0], position)
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
            .where(with_parent(phrase[0], BodyCountList.term) and with_parent(doc, BodyCountList.document))\
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
            select(func.count())\
            .select_from(\
                select(BodyCountList.document)\
                .where(with_parent(phrase[0], BodyCountList.term))\
            )\
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

    k1 = 1.6
    k2 = 1.2
    b = 0.75
    N: int = db.scalar(\
        select(func.count())\
        .select_from(Document)\
    )
    lavg: float = db.scalar(\
        select(func.avg(Document.size()))\
        .select_from(Document)\
    )
    title_Nts: dict[Phrase, int] = {}
    body_Nts: dict[Phrase, int] = {}

    results = [Result(0) for _ in range(top)]
    
    title_phrases: list[Phrase] = []
    body_phrases: list[Phrase] = []
    for phrase in phrases:
        title_terms = []
        body_terms = []
        for token in phrase:
            title_term = db.scalars(\
                select(TitleTerm)\
                .where(TitleTerm.word == token)\
            ).first()
            if title_term is not None:
                title_terms.append(title_term)
            body_term = db.scalars(\
                select(BodyTerm)\
                .where(BodyTerm.word == token)\
            )
            if body_term is not None:
                body_terms.append(body_term)
        title_phrases.append(Phrase(title_terms, nextTitleDoc(title_terms, None)))
        body_phrases.append(Phrase(body_terms, nextBodyDoc(body_terms, None)))

    heapq.heapify(title_phrases)
    heapq.heapify(body_phrases)

    while title_phrases[0].next_doc is not None and body_phrases[0].next_doc is not None:
        title_doc = title_phrases[0].next_doc
        body_doc = title_phrases[0].next_doc

        score = 0
        while title_doc.id <= body_doc.id and title_phrases[0].next_doc == title_doc:
            phrase = title_phrases[0].phrase
            if phrase not in title_Nts:
                title_Nts[phrase] = title_Nt(db, phrase)
            else:
                print("There was a double")
            Nt = title_Nts[phrase]
            ftd = title_ftd(db, phrase, title_doc)
            score += math.log(N/Nt)*(ftd*(k1+1))/(ftd+k1*((1-b)+b*(title_doc.size/lavg)))
            title_phrases[0].next_doc = nextTitleDoc(db, phrase, title_doc)
            title_phrases.sort()
        
        while body_doc.id <= title_doc.id and body_phrases[0].next_doc == body_doc:
            phrase = body_phrases[0].phrase

            # Get the number of times the phrase is present in the documents
            if phrase not in body_Nts:
                body_Nts[phrase] = title_Nt(db, phrase)
            else:
                print("There was a double")
            Nt = title_Nts[phrase]
            ftd = body_ftd(db, phrase, body_doc)
            score += math.log(N/Nt)*(ftd*(k2+1))/(ftd+k2*((1-b)+b*(title_doc.size/lavg)))
            body_phrases[0].next_doc = nextBodyDoc(db, phrase, body_doc)
            body_phrases.sort()

        if score > results[0].score:
            res = Result(score)
            if title_doc.id <= body_doc.id:
                res.doc = title_doc
            else:
                res.doc = body_doc
            heapq.heappushpop(results, res)
    
    return [result.populate() for result in results if result.doc is not None and result.score != 0].reverse()


@current_app.route('/login', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        search_string = request.form['search_str']
        error = None
        
        if not search_string:
            error = 'Please provide a search string'
        
        if error is None:
            res = search_db(search_string)
        
        flash(error)
    
    return render_template('search.html', results = res)