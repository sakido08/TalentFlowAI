"""Request models keep API input validation separate from database tables."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RegisterInput(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value or "." not in value.rsplit("@", 1)[-1]:
            raise ValueError("Enter a valid email address")
        return value


class LoginInput(BaseModel):
    email: str
    password: str


class UserOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
    role: str
    is_active: bool


class EducationInput(BaseModel):
    institution: str = ""
    degree: str = ""
    field: str = ""
    start_date: str = ""
    end_date: str = ""


class ExperienceInput(BaseModel):
    company: str = ""
    position: str = ""
    description: str = ""
    start_date: str = ""
    end_date: str = ""


class CandidateUpdate(BaseModel):
    full_name: str = ""
    email: str = ""
    phone: str = ""
    address: str = ""
    summary: str = ""
    skills: list[str] = Field(default_factory=list)
    education: list[EducationInput] = Field(default_factory=list)
    experience: list[ExperienceInput] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)


class JobInput(BaseModel):
    title: str = Field(min_length=2, max_length=180)
    description: str = ""
    required_skills: str = ""


class MatchInput(BaseModel):
    candidate_id: int
    job_id: int


class RoleInput(BaseModel):
    role: str


class ActiveInput(BaseModel):
    is_active: bool
