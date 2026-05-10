"""User service with full CRUD."""

from models.schemas import User, users_db


def get_all_users() -> list[User]:
    return list(users_db.values())


def get_user(user_id: int) -> User | None:
    return users_db.get(user_id)


def create_user(username: str, email: str, role: str = "user") -> User:
    new_id = max(users_db.keys(), default=0) + 1
    user = User(id=new_id, username=username, email=email, role=role)
    users_db[new_id] = user
    return user


def update_user(user_id: int, **kwargs) -> User | None:
    user = users_db.get(user_id)
    if user is None:
        return None
    for key, value in kwargs.items():
        if hasattr(user, key):
            setattr(user, key, value)
    return user


def delete_user(user_id: int) -> bool:
    if user_id in users_db:
        del users_db[user_id]
        return True
    return False
