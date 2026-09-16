from fastapi import APIRouter
from pydantic import BaseModel

from app.services.company_service import get_company_name, set_company_name

router = APIRouter(prefix="/company", tags=["Company"])


class CompanyIn(BaseModel):
    name: str


@router.get("")
def read_company():
    return {"name": get_company_name()}


@router.put("")
def update_company(body: CompanyIn):
    return {"name": set_company_name(body.name)}
