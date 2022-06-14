from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os

db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:1337@192.168.87.10:5432/rpn")
engine = create_engine(db_url)
Session = sessionmaker(bind=engine)

Base = declarative_base()
