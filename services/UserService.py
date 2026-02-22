from models.User import User
from config.db import get_db

class UserService: 
    @staticmethod
    def get_or_create_user(telegram_id: int, name: str, username: str = None):
        with get_db() as db:
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                user = User(telegram_id=telegram_id, name=name, username=username)
                db.add(user)
                db.commit()
                db.refresh(user)
            return user
    @staticmethod
    def get_user_by_telegram_id(telegram_id: int):
        with get_db() as db:
            return db.query(User).filter(User.telegram_id == telegram_id).first()
    @staticmethod
    def update_username(telegram_id: int, username: str):
        with get_db() as db:
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            if user:
                user.username = username
                db.commit()
                db.refresh(user)
            return user
    @staticmethod
    def delete_user(telegram_id: int):
        with get_db() as db:
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            if user:
                db.delete(user)
                db.commit()
                return True
            return False
    @staticmethod
    def list_users():
        with get_db() as db:
            return db.query(User).all()
    
    