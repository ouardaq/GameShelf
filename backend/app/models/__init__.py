"""Importing this package registers every model on Base.metadata.

Alembic's autogenerate and `Base.metadata.create_all` both rely on that, so keep
new models listed here.
"""

from app.models.game import Game
from app.models.review import Review
from app.models.shelf import ShelfEntry, ShelfStatus
from app.models.user import User

__all__ = ["Game", "Review", "ShelfEntry", "ShelfStatus", "User"]
