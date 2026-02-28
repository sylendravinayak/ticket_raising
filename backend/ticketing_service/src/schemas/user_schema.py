from  pydantic import BaseModel

class UserLogin(BaseModel):
    email: str
    password: str

class UserSignup(BaseModel):
    username: str
    email: str
    password: str

