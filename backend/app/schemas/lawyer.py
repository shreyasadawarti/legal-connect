from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.platform import LegalCategory
from app.models.user import LawyerStatus


class AvailabilitySlot(BaseModel):
    day_of_week: int = Field(ge=0, le=6, description="0=Monday ... 6=Sunday")
    start_time: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    end_time: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")

    @field_validator("end_time")
    @classmethod
    def _end_after_start(cls, v: str, info) -> str:
        if "start_time" in info.data and v < info.data["start_time"]:
            raise ValueError("end_time must be after start_time")
        return v


class LawyerProfileCreate(BaseModel):
    bio: str = Field(default="", max_length=2000)
    years_of_experience: int = Field(default=0, ge=0, le=70)
    categories: list[LegalCategory] = Field(default_factory=lambda: [LegalCategory.OTHER])
    specializations: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    hourly_rate: float = Field(default=0.0, ge=0.0)
    city: Optional[str] = None
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    availability: list[AvailabilitySlot] = Field(default_factory=list)


class LawyerProfileUpdate(BaseModel):
    bio: Optional[str] = Field(default=None, max_length=2000)
    years_of_experience: Optional[int] = Field(default=None, ge=0, le=70)
    categories: Optional[list[LegalCategory]] = None
    specializations: Optional[list[str]] = None
    languages: Optional[list[str]] = None
    hourly_rate: Optional[float] = Field(default=None, ge=0.0)
    city: Optional[str] = None
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    availability: Optional[list[AvailabilitySlot]] = None


class LawyerProfileResponse(BaseModel):
    user_id: str
    name: str
    email: str
    phone: Optional[str] = None
    bio: str = ""
    years_of_experience: int = 0
    categories: list[LegalCategory] = Field(default_factory=lambda: [LegalCategory.OTHER])
    specializations: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    hourly_rate: float = 0.0
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    availability: list[AvailabilitySlot] = Field(default_factory=list)
    avg_rating: float = 0.0
    rating_count: int = 0
    verification_status: LawyerStatus = LawyerStatus.PENDING_VERIFICATION
    is_verified: bool = False
    rejection_reason: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class LawyerProfileListResponse(BaseModel):
    items: list[LawyerProfileResponse]
    total: int
    page: int
    page_size: int


class LawyerSearchQuery(BaseModel):
    q: Optional[str] = None
    category: Optional[LegalCategory] = None
    city: Optional[str] = None
    min_rating: Optional[float] = Field(default=None, ge=0.0, le=5.0)
    verified_only: bool = False
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


def serialize_lawyer_profile(
    profile: dict[str, Any],
    user: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Merge a lawyer profile doc with its owning user account into an API dict."""
    if profile is None:
        return {}
    profile = dict(profile)
    profile["user_id"] = str(profile.pop("user_id", ""))
    profile.pop("_id", None)
    if user:
        profile["name"] = user.get("name", "")
        profile["email"] = user.get("email", "")
        profile["phone"] = user.get("phone")
    else:
        profile.setdefault("name", "")
        profile.setdefault("email", "")
        profile.setdefault("phone", None)
    return profile
