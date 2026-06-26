from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email:    EmailStr
    password: str = Field(min_length=6)
    name:     str = Field(min_length=2)


class LoginRequest(BaseModel):
    email:    EmailStr
    password: str


class AuthResponse(BaseModel):
    token: str
    email: str
    name:  str
    role:  str


class UserResponse(BaseModel):
    id:    int
    email: str
    name:  str
    role:  str

    class Config:
        from_attributes = True
