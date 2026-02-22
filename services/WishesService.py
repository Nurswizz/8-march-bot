from config.db import get_db
from models.Wish import Wish

class WishesService:
    @staticmethod
    def create_wish(user_id: int, wish_text: str):
        with get_db() as db:
            wish = Wish(user_id=user_id, text=wish_text)
            db.add(wish)
            db.commit()
            db.refresh(wish)
            return wish
    @staticmethod
    def get_wishes_by_user_id(user_id: int):
        with get_db() as db:
            return db.query(Wish).filter(Wish.user_id == user_id).all()
    @staticmethod
    def delete_wish(wish_id: int, user_id: int):
        with get_db() as db:
            wish = db.query(Wish).filter(Wish.id == wish_id, Wish.user_id == user_id).first()
            if wish:
                db.delete(wish)
                db.commit()
                return True
            return False
    @staticmethod
    def list_all_wishes():
        with get_db() as db:
            return db.query(Wish).all()