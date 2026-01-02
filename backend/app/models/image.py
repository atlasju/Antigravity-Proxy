from typing import Optional, List, Literal
from pydantic import BaseModel, Field

class ImageGenerationRequest(BaseModel):
    """
    Request model for image generation (OpenAI compatible).
    """
    prompt: str = Field(..., description="A text description of the desired image(s).")
    model: Optional[str] = Field("imagen-3.0-generate-001", description="The model to use for image generation.")
    n: Optional[int] = Field(1, ge=1, le=4, description="The number of images to generate. Must be between 1 and 4.")
    size: Optional[str] = Field("1024x1024", description="The size of the generated images. Must be one of 256x256, 512x512, or 1024x1024.")
    response_format: Optional[Literal["url", "b64_json"]] = Field("url", description="The format in which the generated images are returned.")
    user: Optional[str] = Field(None, description="A unique identifier representing your end-user.")

class Image(BaseModel):
    url: Optional[str] = None
    b64_json: Optional[str] = None
    revised_prompt: Optional[str] = None

class ImageGenerationResponse(BaseModel):
    """
    Response model for image generation (OpenAI compatible).
    """
    created: int
    data: List[Image]
