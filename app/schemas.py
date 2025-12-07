# app/schemas.py
from pydantic import BaseModel
from typing import List, Optional

# --- Steps ---

class Highlight(BaseModel):
    x: Optional[float] = None
    y: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None

# Data coming FROM the extension when creating a guide
class StepCreate(BaseModel):
    # selector: str
    # instruction: str
    # # base64 PNG (will be optional)
    # screenshot: Optional[str] = None
    instruction: Optional[str] = None
    selector: Optional[str] = None
    screenshot: Optional[str] = None
    action: Optional[str] = None
    value: Optional[str] = None

    # Accept nested highlight object
    highlight: Optional[Highlight] = None

    # also accept top-level fields (optional)
    highlight_x: Optional[float] = None
    highlight_y: Optional[float] = None
    highlight_width: Optional[float] = None
    highlight_height: Optional[float] = None

    


# Data going TO the frontend when fetching guides
class Step(BaseModel):
    id: int
    step_number: int
    instruction: str
    selector: str | None = None
    screenshot_path: str | None = None

    highlight_x: float | None = None
    highlight_y: float | None = None
    highlight_width: float | None = None
    highlight_height: float | None = None

    class Config:
        orm_mode = True


# --- Guides ---

class GuideBase(BaseModel):
    name: str
    shortcut: str
    description: str

class GuideCreate(GuideBase):
    name: str
    shortcut: str
    description: Optional[str] = None
    steps: List[StepCreate] = []

class Guide(GuideBase):
    id: int
    name: str
    shortcut: str
    description: Optional[str] = None
    steps: List[Step] = []

    class Config:
        from_attributes = True


# --- Users ---

class UserCreate(BaseModel):
    email: str
    password: str

class User(BaseModel):
    id: int
    email: str
    guides: List[Guide] = []

    class Config:
        from_attributes = True
