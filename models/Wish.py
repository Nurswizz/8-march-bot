from sqlalchemy import Column, Integer, String

from config.db import Base

class Wish(Base):
    __tablename__ = "wishes"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    text = Column(String, nullable=False)

