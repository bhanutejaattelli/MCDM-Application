"""
algorithm.py — Unified Entropy Weight + TOPSIS MCDM pipeline orchestrator.
Consolidated for production deployment.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional

# ── MCDM Algorithm constants ──────────────────────────────────────────────────
QOS_CRITERIA     = ["response_time", "throughput", "security", "cost"]
BENEFIT_CRITERIA = {"throughput", "security"}
COST_CRITERIA    = {"response_time", "cost"}

# ==============================================================================
# ENTROPY WEIGHTS MODULE
# ==============================================================================
@dataclass
class EntropyResult:
    """Holds all intermediate and final outputs of the entropy weight pipeline."""

    attribute_names: list[str]

    # Step 1
    raw_matrix:        np.ndarray = field(repr=False)  # original m × n input
    normalized_matrix: np.ndarray = field(repr=False)  # Step 1 output

    # Step 2
    probability_matrix: np.ndarray = field(repr=False)  # Step 2 output

    # Step 3
    entropy_values: np.ndarray = field(repr=False)       # Step 3 output (1-D, length n)

    # Step 4
    divergence_values: np.ndarray = field(repr=False)    # Step 4 output (1-D, length n)

    # Step 5
    weight_values: np.ndarray = field(repr=False)        # Step 5 output (1-D, length n)

    # Convenience dict: attribute → weight
    weights: dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        if not self.weights:
            self.weights = {
                attr: round(float(w), 6)
                for attr, w in zip(self.attribute_names, self.weight_values)
            }

    def summary(self) -> str:
        """Return a human-readable table of all per-attribute values."""
        lines = [
            f"{'Attribute':<20} {'Entropy':>10} {'Divergence':>12} {'Weight':>10}",
            "-" * 56
        ]
        for attr, e, d, w in zip(
            self.attribute_names,
            self.entropy_values,
            self.divergence_values,
            self.weight_values,
        ):
            lines.append(f"{attr:<20} {e:>10.6f} {d:>12.6f} {w:>10.6f}")
        lines.append("-" * 56)
        lines.append(f"{'SUM':<20} {'':>10} {'':>12} {self.weight_values.sum():>10.6f}")
        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# Step 1 — Normalize the decision matrix
# ══════════════════════════════════════════════════════════════════════════════
def normalize_matrix(matrix: np.ndarray) -> np.ndarray:
    """
    Step 1: Normalise the raw decision matrix column-wise to the range [0, 1].

    Uses min-max normalisation per attribute column:
        r_ij = (x_ij - min_j) / (max_j - min_j)

    If all values in a column are identical, the normalised column is set to
    1/m (uniform) to avoid division-by-zero and preserve entropy meaning.

    Parameters
    ----------
    matrix : np.ndarray, shape (m, n)
        Raw QoS decision matrix.
        Rows = services (alternatives), Columns = attributes (criteria).

    Returns
    -------
    np.ndarray, shape (m, n) — values in [0, 1].
    """
    m, n = matrix.shape
    norm = np.empty_like(matrix, dtype=float)
    for j in range(n):
        col    = matrix[:, j].astype(float)
        col_min = col.min()
        col_max = col.max()
        span   = col_max - col_min
        if span == 0:
            # All services have the same value for this attribute →
            # use uniform distribution so entropy = maximum (weight → 0)
            norm[:, j] = 1.0 / m
        else:
            norm[:, j] = (col - col_min) / span
    return norm


# ══════════════════════════════════════════════════════════════════════════════
# Step 2 — Probability matrix
# ══════════════════════════════════════════════════════════════════════════════
def probability_matrix(normalized: np.ndarray) -> np.ndarray:
    """
    Step 2: Convert normalised values to a column-wise probability distribution.

        p_ij = r_ij / sum_i(r_ij)

    This makes each column a valid discrete probability distribution (sums to 1).
    Zero entries are replaced with a tiny epsilon so that log(p) is always valid.

    Parameters
    ----------
    normalized : np.ndarray, shape (m, n) — output from Step 1.

    Returns
    -------
    np.ndarray, shape (m, n) — where every column sums to 1.
    """
    col_sums = normalized.sum(axis=0)         # shape (n,)
    # Avoid division by zero for all-zero columns
    col_sums = np.where(col_sums == 0, 1e-12, col_sums)
    prob = normalized / col_sums              # broadcast division
    # Clip tiny negatives (numerical noise) and replace zeros
    prob = np.clip(prob, 1e-12, None)
    return prob


# ══════════════════════════════════════════════════════════════════════════════
# Step 3 — Entropy value per attribute
# ══════════════════════════════════════════════════════════════════════════════
def compute_entropy(prob: np.ndarray) -> np.ndarray:
    """
    Step 3: Compute the Shannon information entropy for each attribute column.

        E_j = -1/ln(m) * Σ_i [ p_ij * ln(p_ij) ]

    The factor 1/ln(m) normalises entropy to [0, 1]:
      • E_j = 1  →  all services are identical on this attribute (no info)
      • E_j = 0  →  only one service has a non-zero value (maximum info)

    Parameters
    ----------
    prob : np.ndarray, shape (m, n) — output from Step 2.

    Returns
    -------
    np.ndarray, shape (n,) — entropy value per attribute, in [0, 1].
    """
    m = prob.shape[0]
    k = 1.0 / np.log(m) if m > 1 else 1.0   # normalisation constant

    # Element-wise  p * ln(p);  prob already clipped to > 0 in Step 2
    entropy_matrix = prob * np.log(prob)      # shape (m, n)
    e = -k * entropy_matrix.sum(axis=0)       # shape (n,)

    # Clip to [0, 1] for numerical safety
    return np.clip(e, 0.0, 1.0)


# ══════════════════════════════════════════════════════════════════════════════
# Step 4 — Divergence (degree of variation)
# ══════════════════════════════════════════════════════════════════════════════
def compute_divergence(entropy: np.ndarray) -> np.ndarray:
    """
    Step 4: Calculate the divergence (degree of variation) of each attribute.

        d_j = 1 - E_j

    Interpretation:
      • High divergence → attribute values vary a lot → more discriminating
        → will receive a higher weight.
      • Low divergence  → attribute values similar across services → less useful.

    Parameters
    ----------
    entropy : np.ndarray, shape (n,) — output from Step 3.

    Returns
    -------
    np.ndarray, shape (n,) — divergence per attribute, in [0, 1].
    """
    return 1.0 - entropy


# ══════════════════════════════════════════════════════════════════════════════
# Step 5 — Entropy weights
# ══════════════════════════════════════════════════════════════════════════════
def compute_weights(divergence: np.ndarray) -> np.ndarray:
    """
    Step 5: Normalise divergence values to produce entropy weights.

        w_j = d_j / Σ_k d_k

    The weights sum to exactly 1.0 and represent the relative objective
    importance of each QoS attribute based purely on the data distribution.

    Edge case: if all divergences are 0 (all attributes are constant across
    services), uniform weights 1/n are returned.

    Parameters
    ----------
    divergence : np.ndarray, shape (n,) — output from Step 4.

    Returns
    -------
    np.ndarray, shape (n,) — weights summing to 1.
    """
    total = divergence.sum()
    if total == 0:
        n = len(divergence)
        return np.full(n, 1.0 / n)
    return divergence / total


# ══════════════════════════════════════════════════════════════════════════════
# Public API — full pipeline
# ══════════════════════════════════════════════════════════════════════════════
def compute_entropy_weights(
    matrix: np.ndarray,
    attribute_names: Optional[list[str]] = None,
) -> EntropyResult:
    """
    Run the full 5-step Entropy Weight pipeline on a QoS decision matrix.

    Parameters
    ----------
    matrix : np.ndarray, shape (m, n)
        Raw QoS decision matrix.
        Rows = services/alternatives, Columns = QoS attributes/criteria.
        Must have at least 2 rows (services) for entropy to be meaningful.

    attribute_names : list[str], optional
        Names for each attribute column.
        Defaults to ["attr_0", "attr_1", ...] if not provided.

    Returns
    -------
    EntropyResult
        Dataclass containing all intermediate matrices and the final weight
        dict { attribute_name → weight }.

    Raises
    ------
    ValueError
        If matrix has fewer than 2 rows or no columns.

    Example
    -------
    >>> import numpy as np
    >>> from entropy_weights import compute_entropy_weights
    >>> data = np.array([[120, 850, 88, 250],
    ...                   [110, 920, 91, 220],
    ...                   [130, 800, 87, 270]], dtype=float)
    >>> result = compute_entropy_weights(data, ["RT", "TP", "SEC", "COST"])
    >>> result.weights
    {'RT': ..., 'TP': ..., 'SEC': ..., 'COST': ...}
    """
    if matrix.ndim != 2:
        raise ValueError(f"matrix must be 2-D, got shape {matrix.shape}")
    m, n = matrix.shape
    if m < 2:
        raise ValueError(
            f"At least 2 services (rows) are required for entropy computation. Got {m}."
        )
    if n == 0:
        raise ValueError("matrix must have at least one attribute column.")

    # Default attribute names
    if attribute_names is None:
        attribute_names = [f"attr_{j}" for j in range(n)]
    if len(attribute_names) != n:
        raise ValueError(
            f"len(attribute_names)={len(attribute_names)} does not match "
            f"matrix columns={n}."
        )

    raw = matrix.astype(float)

    # Step 1 — Normalize
    norm  = normalize_matrix(raw)

    # Step 2 — Probability matrix
    prob  = probability_matrix(norm)

    # Step 3 — Entropy per attribute
    ent   = compute_entropy(prob)

    # Step 4 — Divergence per attribute
    div   = compute_divergence(ent)

    # Step 5 — Entropy weights
    wts   = compute_weights(div)

    return EntropyResult(
        attribute_names    = list(attribute_names),
        raw_matrix         = raw,
        normalized_matrix  = norm,
        probability_matrix = prob,
        entropy_values     = ent,
        divergence_values  = div,
        weight_values      = wts,
    )



# ==============================================================================
# TOPSIS MODULE
# ==============================================================================
@dataclass
class TopsisResult:
    """Stores every intermediate output of the TOPSIS pipeline."""

    service_names: list[str]
    criteria:      list[str]
    weights:       np.ndarray = field(repr=False)

    # Step 1
    normalized_matrix: np.ndarray = field(repr=False)

    # Step 2
    weighted_matrix:   np.ndarray = field(repr=False)

    # Step 3
    positive_ideal:    np.ndarray = field(repr=False)   # shape (n,)

    # Step 4
    negative_ideal:    np.ndarray = field(repr=False)   # shape (n,)

    # Step 5
    d_positive:        np.ndarray = field(repr=False)   # shape (m,)  D+
    d_negative:        np.ndarray = field(repr=False)   # shape (m,)  D-

    # Step 6
    closeness_coefficients: np.ndarray = field(repr=False)  # shape (m,)

    # Step 7 — final ranked DataFrame
    ranking_df: pd.DataFrame = field(repr=False)

    @property
    def best_service(self) -> str:
        """Name of the top-ranked service (highest CC)."""
        return self.ranking_df.iloc[0]["service_name"]

    @property
    def scores(self) -> dict[str, float]:
        """Dict: service_name → closeness coefficient (unranked order)."""
        return dict(zip(self.service_names, self.closeness_coefficients.tolist()))

    def summary(self) -> str:
        """Human-readable ranked output table."""
        lines = [
            f"\n{'Rank':<6} {'Service':<22} {'D+':<12} {'D-':<12} {'CC':>10} {'Score (%)':>10}",
            "─" * 72,
        ]
        for _, row in self.ranking_df.iterrows():
            lines.append(
                f"{int(row['rank']):<6} {str(row['service_name']):<22} "
                f"{row['d_positive']:<12.6f} {row['d_negative']:<12.6f} "
                f"{row['closeness_coefficient']:>10.6f} {row['score_pct']:>9.2f}%"
            )
        lines.append("─" * 72)
        lines.append(f"  ⭐  Best service: {self.best_service}")
        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# Step 1 — Normalize the decision matrix
# ══════════════════════════════════════════════════════════════════════════════
def normalize_decision_matrix(matrix: np.ndarray) -> np.ndarray:
    """
    Step 1: Apply vector normalization (Euclidean norm) to each attribute column.

        r_ij = x_ij / sqrt( Σ_i x_ij² )

    This scales all attributes to a common dimensionless range while preserving
    the relative differences between service values more faithfully than min-max.

    Parameters
    ----------
    matrix : np.ndarray, shape (m, n)   — raw decision matrix

    Returns
    -------
    np.ndarray, shape (m, n)            — normalized matrix r
    """
    col_norms = np.sqrt((matrix ** 2).sum(axis=0))   # shape (n,)
    col_norms[col_norms == 0] = 1e-10                # guard zero columns
    return matrix / col_norms


# ══════════════════════════════════════════════════════════════════════════════
# Step 2 — Apply entropy weights to the normalised matrix
# ══════════════════════════════════════════════════════════════════════════════
def apply_weights(normalized: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """
    Step 2: Produce the weighted normalised decision matrix.

        v_ij = w_j × r_ij

    The weights (from the Entropy Weight method) reflect the objective
    importance of each QoS attribute across the observed service data.

    Parameters
    ----------
    normalized : np.ndarray, shape (m, n) — output of Step 1
    weights    : np.ndarray, shape (n,)   — entropy weights (must sum to 1)

    Returns
    -------
    np.ndarray, shape (m, n) — weighted normalised matrix v
    """
    return normalized * weights   # broadcast along rows


# ══════════════════════════════════════════════════════════════════════════════
# Step 3 — Positive Ideal Solution (V+)
# ══════════════════════════════════════════════════════════════════════════════
def positive_ideal_solution(
    weighted: np.ndarray,
    criteria: list[str],
    benefit_criteria: set[str],
    cost_criteria: set[str],
) -> np.ndarray:
    """
    Step 3: Determine the Positive Ideal Solution (V+) — the best possible
    value for each criterion in the weighted normalised matrix.

    Decision rule:
      • Benefit criterion (higher is better) → V+_j = max_i(v_ij)
      • Cost   criterion (lower  is better) → V+_j = min_i(v_ij)

    Parameters
    ----------
    weighted         : np.ndarray, shape (m, n) — output of Step 2
    criteria         : list[str]  — attribute names (length n)
    benefit_criteria : set[str]   — attribute names that are benefit type
    cost_criteria    : set[str]   — attribute names that are cost type

    Returns
    -------
    np.ndarray, shape (n,) — the Positive Ideal Solution vector V+
    """
    n = weighted.shape[1]
    pis = np.zeros(n)
    for j, crit in enumerate(criteria):
        col = weighted[:, j]
        if crit in benefit_criteria:
            pis[j] = col.max()
        elif crit in cost_criteria:
            pis[j] = col.min()
        else:
            # Default: treat unknown criteria as benefit
            pis[j] = col.max()
    return pis


# ══════════════════════════════════════════════════════════════════════════════
# Step 4 — Negative Ideal Solution (V-)
# ══════════════════════════════════════════════════════════════════════════════
def negative_ideal_solution(
    weighted: np.ndarray,
    criteria: list[str],
    benefit_criteria: set[str],
    cost_criteria: set[str],
) -> np.ndarray:
    """
    Step 4: Determine the Negative Ideal Solution (V-) — the worst possible
    value for each criterion in the weighted normalised matrix.

    Decision rule:
      • Benefit criterion (higher is better) → V-_j = min_i(v_ij)
      • Cost   criterion (lower  is better) → V-_j = max_i(v_ij)

    Parameters
    ----------
    weighted         : np.ndarray, shape (m, n) — output of Step 2
    criteria         : list[str]
    benefit_criteria : set[str]
    cost_criteria    : set[str]

    Returns
    -------
    np.ndarray, shape (n,) — the Negative Ideal Solution vector V-
    """
    n = weighted.shape[1]
    nis = np.zeros(n)
    for j, crit in enumerate(criteria):
        col = weighted[:, j]
        if crit in benefit_criteria:
            nis[j] = col.min()
        elif crit in cost_criteria:
            nis[j] = col.max()
        else:
            nis[j] = col.min()
    return nis


# ══════════════════════════════════════════════════════════════════════════════
# Step 5 — Euclidean separation distances
# ══════════════════════════════════════════════════════════════════════════════
def euclidean_distances(
    weighted: np.ndarray,
    pis: np.ndarray,
    nis: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Step 5: Compute the Euclidean distance of each service from V+ and V-.

        D+_i = sqrt( Σ_j (v_ij - V+_j)² )   — distance to Positive Ideal
        D-_i = sqrt( Σ_j (v_ij - V-_j)² )   — distance to Negative Ideal

    Parameters
    ----------
    weighted : np.ndarray, shape (m, n) — output of Step 2
    pis      : np.ndarray, shape (n,)   — output of Step 3
    nis      : np.ndarray, shape (n,)   — output of Step 4

    Returns
    -------
    d_pos : np.ndarray, shape (m,) — D+ distances
    d_neg : np.ndarray, shape (m,) — D- distances
    """
    d_pos = np.sqrt(((weighted - pis) ** 2).sum(axis=1))   # shape (m,)
    d_neg = np.sqrt(((weighted - nis) ** 2).sum(axis=1))   # shape (m,)
    return d_pos, d_neg


# ══════════════════════════════════════════════════════════════════════════════
# Step 6 — Closeness coefficient
# ══════════════════════════════════════════════════════════════════════════════
def closeness_coefficients(
    d_pos: np.ndarray,
    d_neg: np.ndarray,
) -> np.ndarray:
    """
    Step 6: Calculate the Relative Closeness Coefficient (CC) for each service.

        CC_i = D-_i / (D+_i + D-_i)

    Interpretation:
      • CC closer to 1  →  service is near V+  (ideal)  → higher rank
      • CC closer to 0  →  service is near V-  (worst)  → lower rank

    Parameters
    ----------
    d_pos : np.ndarray, shape (m,) — output of Step 5 (D+)
    d_neg : np.ndarray, shape (m,) — output of Step 5 (D-)

    Returns
    -------
    np.ndarray, shape (m,) — CC values in [0, 1]
    """
    denom = d_pos + d_neg
    denom = np.where(denom == 0, 1e-10, denom)   # guard zero denominator
    return d_neg / denom


# ══════════════════════════════════════════════════════════════════════════════
# Step 7 — Rank services
# ══════════════════════════════════════════════════════════════════════════════
def rank_services(
    service_names: list[str],
    criteria: list[str],
    raw_matrix: np.ndarray,
    d_pos: np.ndarray,
    d_neg: np.ndarray,
    cc: np.ndarray,
) -> pd.DataFrame:
    """
    Step 7: Sort services by Closeness Coefficient (descending) and build
    the final ranked results DataFrame.

    Columns in the returned DataFrame
    ──────────────────────────────────
    rank                  : 1-based integer rank (1 = best)
    service_name          : name of the cloud service
    <crit_1> … <crit_n>  : raw QoS values
    d_positive            : D+ Euclidean distance (lower = closer to ideal)
    d_negative            : D- Euclidean distance (higher = farther from worst)
    closeness_coefficient : CC score in [0, 1]
    score_pct             : CC × 100  (percentage format)
    recommendation        : '⭐ BEST CHOICE' for rank-1 service

    Parameters
    ----------
    service_names : list[str]
    criteria      : list[str]
    raw_matrix    : np.ndarray, shape (m, n) — original (unweighted) values
    d_pos         : np.ndarray, shape (m,)
    d_neg         : np.ndarray, shape (m,)
    cc            : np.ndarray, shape (m,)

    Returns
    -------
    pd.DataFrame  — sorted by closeness_coefficient descending, with rank column
    """
    df = pd.DataFrame(raw_matrix, columns=criteria)
    df.insert(0, "service_name", service_names)
    df["d_positive"]            = np.round(d_pos, 6)
    df["d_negative"]            = np.round(d_neg, 6)
    df["closeness_coefficient"] = np.round(cc, 6)
    df["score_pct"]             = np.round(cc * 100, 2)

    df = df.sort_values("closeness_coefficient", ascending=False).reset_index(drop=True)
    df.insert(0, "rank", range(1, len(df) + 1))
    df["recommendation"] = ["⭐ BEST CHOICE" if i == 0 else "" for i in range(len(df))]
    return df


# ══════════════════════════════════════════════════════════════════════════════
# Public API — full pipeline
# ══════════════════════════════════════════════════════════════════════════════
def run_topsis(
    matrix: np.ndarray,
    weights: np.ndarray,
    criteria: list[str],
    service_names: Optional[list[str]] = None,
    benefit_criteria: Optional[set[str]] = None,
    cost_criteria: Optional[set[str]] = None,
) -> TopsisResult:
    """
    Execute the full 7-step TOPSIS algorithm.

    Parameters
    ----------
    matrix           : np.ndarray, shape (m, n)
                       Raw QoS decision matrix.
    weights          : np.ndarray, shape (n,)
                       Entropy weights (summing to 1.0).
    criteria         : list[str], length n
                       QoS attribute names matching column order.
    service_names    : list[str], length m  (optional)
                       Names of the cloud services/alternatives.
                       Defaults to ["Service_0", "Service_1", ...].
    benefit_criteria : set[str]  (optional)
                       Attributes where a higher value is better.
                       Defaults to all criteria if omitted.
    cost_criteria    : set[str]  (optional)
                       Attributes where a lower value is better.

    Returns
    -------
    TopsisResult
        Dataclass with every intermediate array plus the final ranked DataFrame.

    Raises
    ------
    ValueError
        If matrix shape does not match weights / criteria length, or
        fewer than 2 services are provided.
    """
    m, n = matrix.shape
    if m < 2:
        raise ValueError(
            f"At least 2 services (rows) required for TOPSIS. Got {m}."
        )
    if len(criteria) != n:
        raise ValueError(
            f"len(criteria)={len(criteria)} must equal matrix columns={n}."
        )
    if len(weights) != n:
        raise ValueError(
            f"len(weights)={len(weights)} must equal matrix columns={n}."
        )

    if service_names is None:
        service_names = [f"Service_{i}" for i in range(m)]
    if benefit_criteria is None and cost_criteria is None:
        benefit_criteria = set(criteria)
        cost_criteria    = set()
    if benefit_criteria is None:
        benefit_criteria = set(criteria) - set(cost_criteria)
    if cost_criteria is None:
        cost_criteria = set(criteria) - set(benefit_criteria)

    raw = matrix.astype(float)

    # Step 1 — Normalize
    norm = normalize_decision_matrix(raw)

    # Step 2 — Apply weights
    weighted = apply_weights(norm, weights)

    # Step 3 — Positive Ideal Solution (V+)
    pis = positive_ideal_solution(weighted, criteria, benefit_criteria, cost_criteria)

    # Step 4 — Negative Ideal Solution (V-)
    nis = negative_ideal_solution(weighted, criteria, benefit_criteria, cost_criteria)

    # Step 5 — Euclidean distances D+ and D-
    d_pos, d_neg = euclidean_distances(weighted, pis, nis)

    # Step 6 — Closeness Coefficients CC
    cc = closeness_coefficients(d_pos, d_neg)

    # Step 7 — Ranked DataFrame
    ranking = rank_services(service_names, criteria, raw, d_pos, d_neg, cc)

    return TopsisResult(
        service_names          = list(service_names),
        criteria               = list(criteria),
        weights                = weights,
        normalized_matrix      = norm,
        weighted_matrix        = weighted,
        positive_ideal         = pis,
        negative_ideal         = nis,
        d_positive             = d_pos,
        d_negative             = d_neg,
        closeness_coefficients = cc,
        ranking_df             = ranking,
    )



# ==============================================================================
# ORCHESTRATOR
# ==============================================================================
def build_decision_matrix(
    services: list[dict],
) -> tuple[np.ndarray, list[str], list[str]]:
    """
    Convert a list of service dicts into a numpy decision matrix.

    Returns
    -------
    matrix        : np.ndarray (m × n)  — raw QoS values
    service_names : list[str]           — one name per row
    criteria      : list[str]           — QoS columns present in data
    """
    df = pd.DataFrame(services)

    criteria = [c for c in QOS_CRITERIA if c in df.columns]
    if not criteria:
        raise ValueError(
            f"No recognised QoS criteria found. Expected any of: {QOS_CRITERIA}"
        )
    if "service_name" not in df.columns:
        raise ValueError("Each service dict must contain 'service_name'.")

    service_names = df["service_name"].astype(str).tolist()
    matrix = df[criteria].to_numpy(dtype=float)
    return matrix, service_names, criteria


# ── Public ranking API ────────────────────────────────────────────────────────
def run_ranking(
    services: list[dict],
) -> tuple[pd.DataFrame, np.ndarray, list[str]]:
    """
    Full Entropy Weight + TOPSIS pipeline.

    Parameters
    ----------
    services : list[dict]
        Each dict must contain 'service_name' and QoS attribute fields
        (response_time, throughput, security, cost).

    Returns
    -------
    result_df : pd.DataFrame
        Ranked table with columns:
          rank, service_name, <criteria...>,
          d_positive, d_negative, closeness_coefficient, score_pct, recommendation
    weights   : np.ndarray, shape (n,) — entropy weight per criterion
    criteria  : list[str]              — criterion names (column order)

    Raises
    ------
    ValueError  if fewer than 2 services are provided or no QoS columns found.
    """
    if len(services) < 2:
        raise ValueError("At least 2 cloud services are required for ranking.")

    # ── 1. Build decision matrix ───────────────────────────────────────────────
    matrix, service_names, criteria = build_decision_matrix(services)

    # ── 2. Compute Entropy Weights (5-step module) ─────────────────────────────
    ew_result = compute_entropy_weights(matrix, criteria)
    weights   = ew_result.weight_values

    # ── 3. Run TOPSIS (7-step module) ─────────────────────────────────────────
    topsis_result = run_topsis(
        matrix           = matrix,
        weights          = weights,
        criteria         = criteria,
        service_names    = service_names,
        benefit_criteria = BENEFIT_CRITERIA,
        cost_criteria    = COST_CRITERIA,
    )

    return topsis_result.ranking_df, weights, criteria
