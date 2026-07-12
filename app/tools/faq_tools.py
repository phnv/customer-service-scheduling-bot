"""
FAQ stub tool — Milestone 5 placeholder.

Returns hardcoded illustrative answers based on the query keyword.
A real semantic RAG pipeline (ChromaDB + sentence-transformers) will replace
this stub in Milestone 6.
"""

import logging
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


# Stub knowledge base: maps keywords → canned responses
_STUB_KNOWLEDGE: dict[str, str] = {
    "hour": (
        "Our clinic is open Monday to Friday from 8:00 AM to 6:00 PM, "
        "and Saturday from 9:00 AM to 1:00 PM. We are closed on Sundays and public holidays."
    ),
    "price": (
        "Consultation prices vary by specialty and appointment type. "
        "An initial in-person consultation typically ranges from $150 to $300, "
        "and return consultations from $80 to $150. Online consultations are available at a 20% discount."
    ),
    "cancel": (
        "Appointments must be cancelled at least 24 hours in advance to avoid a cancellation fee. "
        "Same-day cancellations may incur a fee of up to 50% of the consultation price."
    ),
    "insurance": (
        "We accept most major health insurance plans. Please contact reception with your insurance details "
        "so we can verify coverage before your appointment."
    ),
    "late": (
        "If you arrive more than 15 minutes late, your appointment may be rescheduled at the doctor's discretion. "
        "Please call us as soon as possible if you expect to be late."
    ),
    "specialty": (
        "Our clinic offers consultations in: Cardiology, Endocrinology, Dermatology, Neurology, "
        "Orthopedics, Pediatrics, Psychiatry, and General Practice."
    ),
    "doctor": (
        "Our medical team includes board-certified specialists across multiple disciplines. "
        "You can ask our scheduling team to find a doctor by specialty or name."
    ),
    "payment": (
        "We accept credit cards, debit cards, and bank transfers. "
        "Payment is required at the time of booking via our secure payment link. "
        "We do not accept cash at this time."
    ),
    "online": (
        "Online consultations are conducted via video call. You will receive a meeting link "
        "after confirming your appointment. A stable internet connection and a quiet environment are recommended."
    ),
    "prepare": (
        "Preparation requirements vary by appointment type. For blood tests, you may need to fast for 8-12 hours. "
        "For specialist consultations, please bring any previous exam results or referral letters."
    ),
}

_DEFAULT_RESPONSE = (
    "Thank you for your question. Our team is happy to assist you with detailed information. "
    "For the most accurate and up-to-date answer, please contact our reception at reception@healthclinic.com "
    "or call us during business hours."
)


@tool
def search_faq_tool(query: str) -> str:
    """
    Searches the clinic's knowledge base for an answer to the user's question.

    Args:
        query: The user's question or topic to search for.

    Returns:
        A string containing relevant clinic information.

    Note:
        This is a stub implementation for Milestone 5.
        A full semantic RAG pipeline will replace this in Milestone 6.
    """
    logger.info(f"Tool 'search_faq_tool' called with query: {query!r}")

    query_lower = query.lower()

    for keyword, response in _STUB_KNOWLEDGE.items():
        if keyword in query_lower:
            logger.info(f"Tool 'search_faq_tool' matched keyword: {keyword!r}")
            return response

    logger.info("Tool 'search_faq_tool' found no matching keyword — returning default response.")
    return _DEFAULT_RESPONSE
