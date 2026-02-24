from sqlalchemy import Boolean, Column, Integer, String, BigInteger

from config.db import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True)
    username = Column(String, nullable=True)
    name = Column(String, nullable=False)
    isAdmin = Column(Boolean, default=False)

