from enum import Enum

from pydantic import BaseModel, Field, model_validator


class EmploymentType(str, Enum):
    salaried = "salaried"
    independent = "independent"
    business_owner = "business_owner"
    other = "other"


class HousingType(str, Enum):
    own = "own"
    rent = "rent"
    family = "family"


class CreditApplication(BaseModel):
    monthly_income: int = Field(3_800_000, ge=650_000, le=50_000_000)
    debt_ratio: float = Field(0.32, ge=0, le=1)
    employment_months: int = Field(36, ge=0, le=600)
    requested_amount: int = Field(8_000_000, ge=200_000, le=100_000_000)
    credit_history_months: int = Field(48, ge=0, le=600)
    late_payments_12m: int = Field(0, ge=0, le=12)
    current_obligations: int = Field(1_200_000, ge=0, le=50_000_000)
    savings_balance: int = Field(2_500_000, ge=0, le=200_000_000)
    external_risk_score: int = Field(72, ge=0, le=100)
    employment_type: EmploymentType = EmploymentType.salaried
    housing_type: HousingType = HousingType.rent


class DecisionThresholds(BaseModel):
    review_min: int = Field(40, ge=1, le=98)
    approval_min: int = Field(70, ge=2, le=99)

    @model_validator(mode="after")
    def validate_order(self) -> "DecisionThresholds":
        if self.approval_min <= self.review_min:
            raise ValueError("approval_min must be greater than review_min")
        return self


class ScoreRequest(BaseModel):
    application: CreditApplication
    thresholds: DecisionThresholds = DecisionThresholds()


class SensitivityItem(BaseModel):
    feature: str
    effect_points: float
    direction: str


class ScoreResponse(BaseModel):
    score: int
    probability_good: float
    decision: str
    model_version: str
    reason_codes: list[str]
    sensitivity: list[SensitivityItem]
    disclaimer: str
