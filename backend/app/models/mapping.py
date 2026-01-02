"""
Model Mapping Model

Allows users to define aliases for models, e.g. mapping 'gpt-4' to 'gemini-1.5-pro'.
"""
from typing import Optional
from sqlmodel import SQLModel, Field

class ModelMapping(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    source_model: str = Field(index=True, unique=True, description="Incoming model name (e.g. gpt-4)")
    target_model: str = Field(description="Target model name (e.g. gemini-1.5-pro)")
    description: Optional[str] = Field(default=None)

class ModelMappingCreate(SQLModel):
    source_model: str
    target_model: str
    description: Optional[str] = None

class ModelMappingRead(SQLModel):
    id: int
    source_model: str
    target_model: str
    description: Optional[str] = None
