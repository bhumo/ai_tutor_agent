from rag.retriever import tokenize
from rag.schemas import TutorDomain


TRUSTED_RESOURCES = {
    TutorDomain.MATH: [
        {"title": "Khan Academy Math", "url": "https://www.khanacademy.org/math", "description": "Courses in algebra, calculus, statistics, probability, and more."},
        {"title": "OpenStax Mathematics", "url": "https://openstax.org/subjects/math", "description": "Peer-reviewed, openly licensed mathematics textbooks."},
    ],
    TutorDomain.PHYSICS: [
        {"title": "Khan Academy High School Physics", "url": "https://www.khanacademy.org/science/highschool-physics", "description": "Lessons on motion, forces, energy, waves, and electromagnetism."},
        {"title": "OpenStax Physics", "url": "https://openstax.org/subjects/science", "description": "Open physics textbooks and supporting material."},
    ],
    TutorDomain.CHEMISTRY: [
        {"title": "Khan Academy Chemistry", "url": "https://www.khanacademy.org/science/chemistry", "description": "Foundational chemistry lessons and practice."},
        {"title": "OpenStax Chemistry 2e", "url": "https://openstax.org/details/books/chemistry-2e", "description": "Peer-reviewed general chemistry textbook."},
    ],
    TutorDomain.BIOLOGY: [
        {"title": "Khan Academy Biology", "url": "https://www.khanacademy.org/science/biology", "description": "Biology lessons from cells through ecology."},
        {"title": "OpenStax Biology 2e", "url": "https://openstax.org/details/books/biology-2e", "description": "Peer-reviewed general biology textbook."},
    ],
    TutorDomain.COMPUTER_SCIENCE: [
        {"title": "Khan Academy Algorithms", "url": "https://www.khanacademy.org/computing/intro-to-algorithms", "description": "Algorithms, searching, sorting, recursion, and graph theory."},
        {"title": "Khan Academy Computing", "url": "https://www.khanacademy.org/computing", "description": "Computer science and programming courses."},
    ],
}


class TrustedResourceSearch:
    """Searches an explicit allow-list; arbitrary user URLs never enter the prompt."""

    def search(self, query: str, domain: TutorDomain, limit: int = 2) -> list[dict[str, str]]:
        query_terms = set(tokenize(query))
        resources = TRUSTED_RESOURCES.get(domain, [])
        return sorted(
            resources,
            key=lambda item: len(query_terms & set(tokenize(item["title"] + " " + item["description"]))),
            reverse=True,
        )[:limit]
