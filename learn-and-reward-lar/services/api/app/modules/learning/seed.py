"""Seed data for local development and demos (English UI/DB/certificate content,
Luxembourgish only as learning content — README sections 15.1 / 18).

Idempotent: only seeds when the courses table is empty.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.learning.models import (
    Course,
    CourseLevel,
    Exercise,
    ExerciseType,
    Lesson,
)

SEED_COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-0000000000c0")

_COURSE: dict[str, object] = {
    "slug": "luxembourgish-for-beginners",
    "title": "Luxembourgish for Beginners",
    "description": (
        "A first course in Luxembourgish (Lëtzebuergesch) covering greetings, numbers and "
        "simple sentences. Built with community-reviewed materials."
    ),
    "level": CourseLevel.BEGINNER,
    "price_coins": 10,
}

_LESSONS: list[dict[str, object]] = [
    {
        "title": "Moien! Greetings and politeness",
        "content": (
            "Learn the everyday greetings of Luxembourgish. In Luxembourg it is normal to "
            "greet shopkeepers and neighbours, so these phrases get used daily."
        ),
        "vocabulary": [
            {"term": "Moien", "translation": "Hello", "pronunciation": "MOY-en"},
            {"term": "Gudde Moien", "translation": "Good morning", "pronunciation": "GOO-de MOY-en"},
            {"term": "Merci vill", "translation": "Thank you very much", "pronunciation": "MER-see vil"},
            {"term": "Äddi", "translation": "Goodbye", "pronunciation": "AH-dee"},
            {"term": "Wéi geet et?", "translation": "How are you?", "pronunciation": "HWAY gay-et"},
        ],
        "exercises": [
            {
                "type": ExerciseType.MULTIPLE_CHOICE,
                "prompt": "Which phrase means \"Hello\" in Luxembourgish?",
                "options": ["Merci vill", "Moien", "Äddi", "Eent"],
                "answer": {"value": 1},
                "explanation": "Moien is the standard informal hello.",
            },
            {
                "type": ExerciseType.FILL_IN_BLANK,
                "prompt": "Fill in the blank: \"___ vill!\" means \"Thank you very much!\".",
                "options": None,
                "answer": {"value": "Merci", "alternatives": ["merci"]},
                "explanation": "Merci vill = thank you very much.",
            },
        ],
    },
    {
        "title": "Numbers: counting from one to five",
        "content": (
            "Counting in Luxembourgish. Practice the first five numbers; they appear in "
            "prices, times and everyday conversation."
        ),
        "vocabulary": [
            {"term": "eent", "translation": "one", "pronunciation": "AYNT"},
            {"term": "zwee", "translation": "two", "pronunciation": "TSVAY"},
            {"term": "dräi", "translation": "three", "pronunciation": "DRAY"},
            {"term": "véier", "translation": "four", "pronunciation": "FAY-er"},
            {"term": "fënnef", "translation": "five", "pronunciation": "FEN-ef"},
        ],
        "exercises": [
            {
                "type": ExerciseType.MULTIPLE_CHOICE,
                "prompt": "What is \"three\" in Luxembourgish?",
                "options": ["zwee", "véier", "dräi", "fënnef"],
                "answer": {"value": 2},
                "explanation": "dräi = three.",
            },
            {
                "type": ExerciseType.TRANSLATION,
                "prompt": "Translate to Luxembourgish: \"five\"",
                "options": None,
                "answer": {"value": "fënnef", "alternatives": ["fennef"]},
                "explanation": "fënnef = five.",
            },
        ],
    },
    {
        "title": "Simple sentences about yourself",
        "content": (
            "Introduce yourself: where you are from and what you have. Luxembourgish "
            "present-tense sentences are short and friendly."
        ),
        "vocabulary": [
            {"term": "Ech sinn ...", "translation": "I am ...", "pronunciation": "esh sin"},
            {"term": "Ech hunn ...", "translation": "I have ...", "pronunciation": "esh hun"},
            {
                "term": "Ech sinn aus Lëtzebuerg",
                "translation": "I am from Luxembourg",
                "pronunciation": "esh sin ows LETS-ebu-esh",
            },
        ],
        "exercises": [
            {
                "type": ExerciseType.TRANSLATION,
                "prompt": "Translate to Luxembourgish: \"I am from Luxembourg.\"",
                "options": None,
                "answer": {
                    "value": "Ech sinn aus Lëtzebuerg",
                    "alternatives": ["ech sinn aus letzebuerg", "ech sinn aus lëtzebuerg."],
                },
                "explanation": "Ech sinn aus ... = I am from ...",
            },
            {
                "type": ExerciseType.FILL_IN_BLANK,
                "prompt": "Fill in the blank: \"___ hunn e Buch.\" means \"I have a book.\"",
                "options": None,
                "answer": {"value": "Ech", "alternatives": ["ech"]},
                "explanation": "Ech hunn = I have.",
            },
        ],
    },
]


def seed_if_empty(db: Session) -> bool:
    """Seed the demo course. Returns True when seeding happened."""
    existing = db.scalar(select(func.count()).select_from(Course))
    if existing:
        return False

    course = Course(
        slug=_COURSE["slug"],
        title=_COURSE["title"],
        description=_COURSE["description"],
        language="lb",
        level=_COURSE["level"],
        price_coins=_COURSE["price_coins"],
        is_published=True,
        community_id=SEED_COMMUNITY_ID,
    )
    db.add(course)
    db.flush()

    for order_index, lesson_spec in enumerate(_LESSONS):
        lesson = Lesson(
            course_id=course.id,
            order_index=order_index,
            title=lesson_spec["title"],
            content=lesson_spec["content"],
            vocabulary=lesson_spec["vocabulary"],
        )
        db.add(lesson)
        db.flush()
        exercises = lesson_spec["exercises"]
        assert isinstance(exercises, list)
        for exercise_order, exercise_spec in enumerate(exercises):
            db.add(
                Exercise(
                    lesson_id=lesson.id,
                    order_index=exercise_order,
                    type=exercise_spec["type"],
                    prompt=exercise_spec["prompt"],
                    options=exercise_spec["options"],
                    answer=exercise_spec["answer"],
                    explanation=exercise_spec["explanation"],
                )
            )
    db.flush()
    return True
