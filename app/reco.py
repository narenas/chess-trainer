from datetime import datetime
from typing import List
from .models import RecoItem, TaskDB

# Mix objetivo simple por categoría (puedes ajustar por usuario)
TARGET_MIX = {
    "tactics": 0.35,
    "strategy": 0.20,
    "endgames": 0.15,
    "openings": 0.15,
    "analysis": 0.15,
}


def score_task(task: TaskDB, weekly_done_by_cat: dict[str, int]) -> tuple[float, str]:
    # Gap de cobertura: más puntos si esa categoría va por debajo del objetivo
    total_done = sum(weekly_done_by_cat.values()) or 1
    done_pct = weekly_done_by_cat.get(task.category, 0) / total_done
    target = TARGET_MIX.get(task.category, 0.1)
    coverage = max(target - done_pct, 0)  # 0..1

    # Frescura: tareas más antiguas un pequeño boost
    age_days = max((datetime.utcnow() - task.created_at).days, 0)
    freshness = min(age_days / 14.0, 1.0)  # 0..1

    # Prioridad del usuario
    prio = (task.priority or 50) / 100.0

    score = 0.5 * coverage + 0.3 * freshness + 0.2 * prio
    reason = f"coverage_gap={coverage:.2f}, freshness={freshness:.2f}, prio={prio:.2f}"
    return score, reason


def rank_tasks(candidates: List[TaskDB], weekly_done_by_cat: dict[str, int], k: int = 3) -> List[RecoItem]:
    scored: list[tuple[TaskDB, float, str]] = []
    for t in candidates:
        s, r = score_task(t, weekly_done_by_cat)
        scored.append((t, s, r))
    top = sorted(scored, key=lambda x: x[1], reverse=True)[:k]
    return [RecoItem(task_id=t.id, score=s, reason=r) for t, s, r in top]
