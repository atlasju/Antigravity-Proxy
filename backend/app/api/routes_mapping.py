"""
Model Mapping API Routes

Manage dynamic model mappings.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.core.database import get_session
from app.models.mapping import ModelMapping, ModelMappingCreate, ModelMappingRead

router = APIRouter()

@router.get("/", response_model=list[ModelMappingRead])
def list_mappings(session: Session = Depends(get_session)):
    mappings = session.exec(select(ModelMapping)).all()
    return mappings

@router.post("/", response_model=ModelMappingRead)
def create_mapping(mapping: ModelMappingCreate, session: Session = Depends(get_session)):
    # Check if exists
    existing = session.exec(select(ModelMapping).where(ModelMapping.source_model == mapping.source_model)).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Mapping for {mapping.source_model} already exists")
    
    db_mapping = ModelMapping.model_validate(mapping)
    session.add(db_mapping)
    session.commit()
    session.refresh(db_mapping)
    return db_mapping

@router.delete("/{mapping_id}")
def delete_mapping(mapping_id: int, session: Session = Depends(get_session)):
    mapping = session.get(ModelMapping, mapping_id)
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found")
    session.delete(mapping)
    session.commit()
    return {"ok": True}
