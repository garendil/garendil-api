import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)


class ScoringAuditLog:
    """Registra cambios de scoring para auditoría y rollback."""

    @staticmethod
    async def log_score_change(
        db: AsyncSession,
        funcionario_id: int,
        old_score: float,
        new_score: float,
        layer1: float,
        layer2: float,
        layer3: Optional[float] = None,
        reason: str = "automatic recalculation",
    ) -> bool:
        try:
            await db.execute(
                text(
                    """
                    INSERT INTO scoring_audit_log
                        (funcionario_id, ier_score_old, ier_score_new,
                         layer1_score, layer2_score, layer3_score, change_reason)
                    VALUES (:func_id, :old, :new, :l1, :l2, :l3, :reason)
                    """
                ),
                {
                    "func_id": funcionario_id,
                    "old": old_score,
                    "new": new_score,
                    "l1": layer1,
                    "l2": layer2,
                    "l3": layer3,
                    "reason": reason,
                },
            )
            await db.commit()
            return True
        except Exception as e:
            logger.error(f"Error logging score change: {e}")
            return False
