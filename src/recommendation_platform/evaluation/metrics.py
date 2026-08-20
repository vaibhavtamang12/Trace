from __future__ import annotations

from collections.abc import Iterable

import numpy as np


def precision_at_k(recommended: Iterable[str], relevant: set[str], k: int = 10) -> float:
    values = list(recommended)[:k]
    return sum(item in relevant for item in values) / max(len(values), 1)


def recall_at_k(recommended: Iterable[str], relevant: set[str], k: int = 10) -> float:
    if not relevant:
        return 0.0
    values = list(recommended)[:k]
    return sum(item in relevant for item in values) / len(relevant)


def average_precision_at_k(recommended: Iterable[str], relevant: set[str], k: int = 10) -> float:
    if not relevant:
        return 0.0
    score = 0.0
    hits = 0
    for index, item in enumerate(list(recommended)[:k], start=1):
        if item in relevant:
            hits += 1
            score += hits / index
    return score / min(len(relevant), k)


def ndcg_at_k(recommended: Iterable[str], relevant: set[str], k: int = 10) -> float:
    values = list(recommended)[:k]
    gains = np.array([1.0 if item in relevant else 0.0 for item in values])
    discounts = np.log2(np.arange(2, len(gains) + 2))
    dcg = float(np.sum(gains / discounts))
    ideal = min(len(relevant), k)
    if ideal == 0:
        return 0.0
    idcg = float(np.sum(np.ones(ideal) / np.log2(np.arange(2, ideal + 2))))
    return dcg / idcg


def hit_rate_at_k(recommended: Iterable[str], relevant: set[str], k: int = 10) -> float:
    return float(any(item in relevant for item in list(recommended)[:k]))


def ranking_report(
    recommended_by_user: dict[str, list[str]], relevant_by_user: dict[str, set[str]], k: int = 10
) -> dict[str, float]:
    users = sorted(set(recommended_by_user) & set(relevant_by_user))
    if not users:
        return {name: 0.0 for name in ["precision", "recall", "map", "ndcg", "hit_rate"]}
    values = {
        "precision": [
            precision_at_k(recommended_by_user[user], relevant_by_user[user], k) for user in users
        ],
        "recall": [
            recall_at_k(recommended_by_user[user], relevant_by_user[user], k) for user in users
        ],
        "map": [
            average_precision_at_k(recommended_by_user[user], relevant_by_user[user], k)
            for user in users
        ],
        "ndcg": [ndcg_at_k(recommended_by_user[user], relevant_by_user[user], k) for user in users],
        "hit_rate": [
            hit_rate_at_k(recommended_by_user[user], relevant_by_user[user], k) for user in users
        ],
    }
    return {key: round(float(np.mean(value)), 6) for key, value in values.items()}
