from fastapi import APIRouter,HTTPException
from pydantic import BaseModel
from typing import Optional,Dict,Any
from app.services.review_service import *
router=APIRouter(prefix="/reviews",tags=["Reviews"])
class In(BaseModel):requirement:str;analysis:Dict[str,Any]={};draft_response:Optional[str]=None
class Decision(BaseModel):status:str;edited_response:Optional[str]=None;notes:Optional[str]=None
@router.post("")
def create(x:In):return create_review(x.model_dump())
@router.get("")
def all():return list_reviews()
@router.patch("/{id}")
def patch(id:str,x:Decision):
 r=decide(id,x.status,x.edited_response,x.notes)
 if not r:raise HTTPException(404,"Review not found")
 return r
