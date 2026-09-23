import re

CATEGORIES = (
    "Technical", "Legal", "Security", "Compliance",
    "Commercial", "Pricing", "Support", "Experience",
)

# "must/should/will support X" uses "support" as a verb (a technical
# capability), not as a noun referring to a support/SLA requirement
# ("24/7 incident support", "provide enterprise support"). Naive substring
# matching on "support" alone misclassifies the former as the latter.
_SUPPORT_AS_VERB = re.compile(r"\b(must|should|shall|will|to|can|does|do)\s+support\b")


def classify_category(text: str) -> str:
    low = text.lower()
    if any(k in low for k in ("price", "pricing", "cost", "fee", "payment")):
        return "Pricing"
    if any(k in low for k in ("security", "encrypt", "privacy", "iso", "soc", "certif", "pci", "hipaa", "fedramp")):
        return "Security"
    if any(k in low for k in ("compliance", "regulation", "policy", "audit", "law", "legal", "contract")):
        return "Legal"
    if "support" in low and not _SUPPORT_AS_VERB.search(low):
        return "Support"
    if any(k in low for k in ("sla", "uptime", "response time")):
        return "Support"
    if any(k in low for k in ("experience", "case study", "track record", "reference", "prior project")):
        return "Experience"
    if any(k in low for k in ("commercial", "warranty", "liability", "insurance")):
        return "Commercial"
    return "Technical"


def classify_mandatory(text: str) -> bool:
    low = text.lower()
    if any(k in low for k in ("should", "may", "preferred", "optional", "nice to have", "desirable")):
        return False
    return True
