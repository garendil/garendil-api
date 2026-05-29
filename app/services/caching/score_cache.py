import json
import logging
from typing import Any, Dict, Optional

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

_TTL_SECONDS = 7 * 24 * 3600  # 7 días


class ScoreCache:
    """
    Caché de IER scores en Redis.
    TTL: 7 días. Fallos silenciosos — la API sigue funcionando sin caché.
    """

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self._redis: Optional[aioredis.Redis] = None

    async def connect(self) -> None:
        try:
            self._redis = aioredis.from_url(self.redis_url, decode_responses=True)
        except Exception as e:
            logger.warning(f"ScoreCache: no se pudo conectar a Redis: {e}")
            self._redis = None

    async def disconnect(self) -> None:
        if self._redis:
            await self._redis.aclose()
            self._redis = None

    def _key(self, funcionario_id: int) -> str:
        return f"score:{funcionario_id}:v3"

    async def get(self, funcionario_id: int) -> Optional[Dict[str, Any]]:
        if not self._redis:
            return None
        try:
            value = await self._redis.get(self._key(funcionario_id))
            return json.loads(value) if value else None
        except Exception as e:
            logger.warning(f"ScoreCache.get error: {e}")
            return None

    async def set(self, funcionario_id: int, score_data: Dict[str, Any]) -> bool:
        if not self._redis:
            return False
        try:
            await self._redis.setex(
                self._key(funcionario_id),
                _TTL_SECONDS,
                json.dumps(score_data),
            )
            return True
        except Exception as e:
            logger.warning(f"ScoreCache.set error: {e}")
            return False

    async def invalidate(self, funcionario_id: int) -> bool:
        if not self._redis:
            return False
        try:
            await self._redis.delete(self._key(funcionario_id))
            return True
        except Exception as e:
            logger.warning(f"ScoreCache.invalidate error: {e}")
            return False

    async def invalidate_batch(self, funcionario_ids: list) -> int:
        return sum([await self.invalidate(fid) for fid in funcionario_ids])

    async def clear_all(self) -> bool:
        if not self._redis:
            return False
        try:
            keys = await self._redis.keys("score:*")
            if keys:
                await self._redis.delete(*keys)
                logger.warning(f"ScoreCache: eliminadas {len(keys)} keys")
            return True
        except Exception as e:
            logger.warning(f"ScoreCache.clear_all error: {e}")
            return False
