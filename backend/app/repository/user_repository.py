"""User repository."""

from datetime import datetime

from app.models.user import RefreshToken, User
from app.repository.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self) -> None:
        super().__init__(User)

    async def get_by_email(self, email: str) -> User | None:
        return await self.find_one({"email": email.lower()})

    async def create_user(
        self,
        email: str,
        hashed_password: str,
        full_name: str,
    ) -> User:
        return await self.create(
            {
                "email": email.lower(),
                "hashed_password": hashed_password,
                "full_name": full_name,
            }
        )


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    def __init__(self) -> None:
        super().__init__(RefreshToken)

    async def store(self, user_id: str, token_hash: str, expires_at: datetime) -> RefreshToken:
        return await self.create(
            {
                "user_id": user_id,
                "token_hash": token_hash,
                "expires_at": expires_at,
            }
        )

    async def get_valid(self, token_hash: str) -> RefreshToken | None:
        token = await self.find_one({"token_hash": token_hash, "revoked": False})
        if token and token.expires_at < datetime.utcnow():
            return None
        return token

    async def revoke(self, token_hash: str) -> None:
        token = await self.find_one({"token_hash": token_hash})
        if token:
            token.revoked = True
            await token.save()
