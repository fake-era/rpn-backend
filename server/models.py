from sqlalchemy import Column, Integer, String, DateTime, func
from base import Base


class Result(Base):
    __tablename__ = 'result'
    id = Column(Integer, primary_key=True, index=True)
    iin = Column(String)
    address = Column(String)
    numbers = Column(String)
    status_osms = Column(String)
    categories_osms = Column(String)
    relatives = Column(String)
    death_date = Column(String)
    data_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Task(Base):
    __tablename__ = "task"
    id = Column(Integer, primary_key=True, index=True)
    iin = Column(String)
    status = Column(String, default="new")


class Token(Base):
    __tablename__ = "token"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String)
    date_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
