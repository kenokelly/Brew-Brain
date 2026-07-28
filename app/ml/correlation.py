"""
Multi-batch cross-correlation & Dynamic Time Warping (DTW) service.

Computes kinetic shape similarity between active batch gravity velocity curves
and historical peer batches, identifying anomalous fermentation profiles.
"""

import math
from typing import List, Dict, Any, Optional


def calculate_dtw_distance(seq1: List[float], seq2: List[float]) -> float:
    """
    Calculate Dynamic Time Warping (DTW) distance between two numerical time-series.

    Args:
        seq1: First sequence of numbers (e.g. active velocity curve).
        seq2: Second sequence of numbers (e.g. historical velocity curve).

    Returns:
        DTW distance value (float >= 0.0).
    """
    if not seq1 or not seq2:
        return 0.0

    n, m = len(seq1), len(seq2)
    dtw_matrix = [[float("inf")] * (m + 1) for _ in range(n + 1)]
    dtw_matrix[0][0] = 0.0

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = abs(seq1[i - 1] - seq2[j - 1])
            dtw_matrix[i][j] = cost + min(
                dtw_matrix[i - 1][j],      # Insertion
                dtw_matrix[i][j - 1],      # Deletion
                dtw_matrix[i - 1][j - 1],  # Match
            )

    return dtw_matrix[n][m]


def calculate_cross_correlation_score(active_curve: List[float], peer_curve: List[float]) -> float:
    """
    Convert DTW distance between two curves into a normalized similarity score S in [0.0, 1.0].

    Args:
        active_curve: Active batch SG velocity time series.
        peer_curve: Historical peer batch SG velocity time series.

    Returns:
        Similarity score float between 0.0 (unrelated) and 1.0 (identical).
    """
    if not active_curve or not peer_curve:
        return 1.0

    dtw_dist = calculate_dtw_distance(active_curve, peer_curve)
    # Scale distance to [0, 1] similarity score
    score = 1.0 / (1.0 + (dtw_dist / max(1, len(active_curve))))
    return round(score, 3)


def find_best_peer_batch(
    active_curve: List[float],
    peer_batches: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Evaluate active batch against historical peer batches to find top kinetic match.

    Args:
        active_curve: List of SG velocity readings for active batch.
        peer_batches: List of dicts, each containing 'batch_id' and 'velocity_curve'.

    Returns:
        Dict with best_peer_id, correlation_score, and is_anomalous status (< 0.70).
    """
    if not active_curve or not peer_batches:
        return {
            "best_peer_id": None,
            "correlation_score": 1.0,
            "is_anomalous": False,
        }

    best_peer_id = None
    best_score = -1.0

    for peer in peer_batches:
        peer_id = peer.get("batch_id")
        peer_curve = peer.get("velocity_curve", [])

        if not peer_id or not peer_curve:
            continue

        score = calculate_cross_correlation_score(active_curve, peer_curve)
        if score > best_score:
            best_score = score
            best_peer_id = peer_id

    if best_score < 0:
        best_score = 1.0

    is_anomalous = best_score < 0.70

    return {
        "best_peer_id": best_peer_id,
        "correlation_score": best_score,
        "is_anomalous": is_anomalous,
    }
