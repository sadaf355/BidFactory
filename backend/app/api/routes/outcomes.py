from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional,List
from app.services.outcome_service import *
router=APIRouter(prefix="/outcomes",tags=["Outcomes"])
class In(BaseModel):rfp_name:str;outcome:str;notes:Optional[str]=None;lessons:List[str]=[]
@router.post("")
def create(x:In):return record(x.model_dump())
@router.get("") 
def all():return list_outcomes()
@router.get("/memory")
def memory():return list_memory()
