from pydantic import BaseModel, constr


class Result(BaseModel):
    iin: constr(min_length=12, max_length=12)
    address: str | None
    numbers: str | None
    status_osms: str | None
    categories_osms: str | None
    relatives: str | None
    death_date: str | None

    class Config:
        orm_mode = True


class Task(BaseModel):
    iin: constr(min_length=12, max_length=12)
    status: str = 'new'

    class Config:
        orm_mode = True


class Token(BaseModel):
    token: str

    class Config:
        orm_mode = True
