from sqlalchemy import CheckConstraint, Column, Integer, String

from config.db import Base

class Wish(Base):
    __tablename__ = "wishes"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    text = Column(String, nullable=False)
    priority = Column(Integer, nullable=False, default=5)

    __table_args__ = (
        CheckConstraint("priority >= 1 AND priority <= 10", name="priority_range"),
    )