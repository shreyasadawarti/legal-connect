from fastapi import APIRouter

from app.models.platform import LegalCategory

router = APIRouter(prefix="/legal-categories", tags=["legal-categories"])

CATEGORY_DESCRIPTIONS: dict[LegalCategory, str] = {
    LegalCategory.FAMILY: "Divorce, custody, adoption and family disputes",
    LegalCategory.CRIMINAL: "Criminal defence and prosecution matters",
    LegalCategory.CIVIL: "General civil disputes and litigation",
    LegalCategory.CORPORATE: "Business formation, governance and compliance",
    LegalCategory.PROPERTY: "Real estate, tenancy and property disputes",
    LegalCategory.TAX: "Tax filing, disputes and advisory",
    LegalCategory.LABOR: "Employment, workplace and labour disputes",
    LegalCategory.INTELLECTUAL_PROPERTY: "Patents, trademarks and copyrights",
    LegalCategory.CONTRACT: "Contract drafting, review and disputes",
    LegalCategory.PERSONAL_INJURY: "Accident and injury compensation claims",
    LegalCategory.IMMIGRATION: "Visas, residency and citizenship matters",
    LegalCategory.OTHER: "Other legal assistance",
}


@router.get("")
async def list_categories():
    return [
        {
            "name": cat.value,
            "label": cat.name.replace("_", " ").title(),
            "description": CATEGORY_DESCRIPTIONS[cat],
        }
        for cat in LegalCategory
    ]
