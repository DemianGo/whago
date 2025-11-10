"""
Schemas Pydantic para usuários e autenticação.

Inclui validações exigidas pelo PRD:
- Nome completo entre 2 e 100 caracteres
- Email válido e único (verificado no serviço)
- Senha forte (mínimo 8 chars, 1 maiúscula, 1 número, 1 especial)
- Telefone no formato internacional +55 DD 9XXXX-XXXX
- CPF/CNPJ com validação de dígitos verificadores
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional
from uuid import UUID

import phonenumbers
from pydantic import BaseModel, EmailStr, Field, field_validator


PASSWORD_REGEX = re.compile(
    r"^(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*(),.?\":{}|<>_\-]).{8,}$"
)


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def _validate_cpf(value: str) -> bool:
    numbers = _digits(value)
    if len(numbers) != 11 or numbers == numbers[0] * 11:
        return False

    for i in range(9, 11):
        sum_ = sum(int(numbers[num]) * ((i + 1) - num) for num in range(0, i))
        digit = ((sum_ * 10) % 11) % 10
        if int(numbers[i]) != digit:
            return False
    return True


def _validate_cnpj(value: str) -> bool:
    numbers = _digits(value)
    if len(numbers) != 14:
        return False

    weight_first = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    weight_second = [6] + weight_first

    def calculate_digit(nums: str, weights: list[int]) -> str:
        total = sum(int(num) * weight for num, weight in zip(nums, weights, strict=False))
        remainder = total % 11
        return "0" if remainder < 2 else str(11 - remainder)

    first_digit = calculate_digit(numbers[:12], weight_first)
    second_digit = calculate_digit(numbers[:13], weight_second)
    return numbers[-2:] == f"{first_digit}{second_digit}"


class UserBase(BaseModel):
    """Campos base de usuários."""

    email: EmailStr
    name: str = Field(min_length=2, max_length=100)
    phone: str = Field(description="Formato internacional: +5511999999999")
    company_name: Optional[str] = Field(default=None, max_length=150)
    document: Optional[str] = Field(
        default=None,
        description="CPF ou CNPJ sem máscara.",
    )
    plan_slug: Optional[str] = Field(
        default="free",
        description="Slug do plano desejado. Default = free.",
    )

    model_config = {"extra": "forbid", "str_strip_whitespace": True}

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        """Garante que o telefone está no formato internacional válido."""

        try:
            parsed_number = phonenumbers.parse(value, None)
        except phonenumbers.NumberParseException as exc:
            raise ValueError("Telefone inválido. Use formato +5511999999999.") from exc

        if not phonenumbers.is_possible_number(parsed_number) or not phonenumbers.is_valid_number(parsed_number):
            raise ValueError("Telefone inválido. Use formato +5511999999999.")

        if parsed_number.country_code != 55:
            raise ValueError("Somente telefones brasileiros são suportados no MVP.")

        national_number = str(parsed_number.national_number)
        if len(national_number) not in (10, 11):
            raise ValueError("Telefone deve possuir 10 ou 11 dígitos.")

        return phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)

    @field_validator("document")
    @classmethod
    def validate_document(cls, value: Optional[str]) -> Optional[str]:
        """Valida CPF/CNPJ conforme dígitos verificadores."""

        if value is None:
            return value

        digits = _digits(value)
        if len(digits) == 11 and _validate_cpf(digits):
            return digits
        if len(digits) == 14 and _validate_cnpj(digits):
            return digits
        raise ValueError("Documento inválido. Informe CPF (11) ou CNPJ (14) válido.")


class UserCreate(UserBase):
    """Schema de criação de usuário (registro)."""

    password: str = Field(max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        """Garante complexidade mínima da senha conforme PRD."""

        if len(value) < 8:
            raise ValueError(
                "Senha deve possuir ao menos 8 caracteres, incluindo 1 maiúscula, "
                "1 número e 1 caractere especial."
            )
        if not PASSWORD_REGEX.match(value):
            raise ValueError(
                "Senha deve possuir ao menos 8 caracteres, incluindo 1 maiúscula, "
                "1 número e 1 caractere especial."
            )
        return value


class UserLogin(BaseModel):
    """Credenciais para login."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    model_config = {"extra": "forbid"}


class ForgotPasswordRequest(BaseModel):
    """Schema para solicitação de recuperação de senha."""

    email: EmailStr

    model_config = {"extra": "forbid"}


class ResetPasswordRequest(BaseModel):
    """Schema para redefinição de senha."""

    token: str = Field(min_length=10, max_length=256)
    new_password: str = Field(max_length=128)

    model_config = {"extra": "forbid"}

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        """Aplica as mesmas regras de senha forte do registro."""

        if len(value) < 8:
            raise ValueError(
                "Senha deve possuir ao menos 8 caracteres, incluindo 1 maiúscula, "
                "1 número e 1 caractere especial."
            )
        if not PASSWORD_REGEX.match(value):
            raise ValueError(
                "Senha deve possuir ao menos 8 caracteres, incluindo 1 maiúscula, "
                "1 número e 1 caractere especial."
            )
        return value


class UserPublic(BaseModel):
    """Representação pública do usuário."""

    id: UUID
    email: EmailStr
    name: str
    phone: str
    company_name: Optional[str]
    document: Optional[str]
    credits: int
    plan: Optional[str]
    plan_slug: Optional[str] = None
    plan_features: Optional[dict] = None
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TokenPair(BaseModel):
    """Resposta padrão de tokens."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    """Resposta agregada contendo usuário e tokens."""

    user: UserPublic
    tokens: TokenPair


class UserUpdate(BaseModel):
    """Schema para atualização de perfil do usuário."""

    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    phone: Optional[str] = None
    company_name: Optional[str] = Field(default=None, max_length=150)
    document: Optional[str] = None
    plan_slug: Optional[str] = None

    model_config = {"extra": "forbid"}

    @field_validator("phone")
    @classmethod
    def validate_phone_optional(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        return UserBase.validate_phone(value)

    @field_validator("document")
    @classmethod
    def validate_document_optional(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        return UserBase.validate_document(value)


