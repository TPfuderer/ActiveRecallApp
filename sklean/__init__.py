"""sklean: lightweight tabular data validation utilities.

This module exposes a single public function, :func:`validate`, designed for quick
quality checks on pandas DataFrames before exploratory analysis or machine-learning
training.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

__all__ = ["validate"]


def _check_missing(df: pd.DataFrame) -> bool:
    """Check whether the DataFrame contains missing values.

    Missing values are one of the most common quality issues in real-world data.
    In ML pipelines, null entries can silently propagate and trigger downstream
    failures (for example, estimators that do not accept NaNs) or introduce bias
    when rows are dropped without careful analysis.

    This helper computes how many columns contain at least one missing value and
    prints a short summary suitable for command-line workflows.

    Parameters
    ----------
    df:
        The DataFrame to inspect.

    Returns
    -------
    bool
        ``True`` when an issue is found (one or more columns contain missing
        values), otherwise ``False``.

    Notes
    -----
    Typical remediation strategies include:

    * Domain-aware imputation (mean/median/mode is a baseline, but often not
      sufficient).
    * Missing-indicator features when the fact that data is missing carries
      predictive signal.
    * Collecting additional data when missingness is systematic.
    """

    missing_cols = int(df.isna().any(axis=0).sum())
    if missing_cols:
        print(f"[Missing Values] Found in {missing_cols} columns.")
        return True
    print("[Missing Values] None.")
    return False


def _check_duplicates(df: pd.DataFrame) -> bool:
    """Check for duplicate rows in the DataFrame.

    Duplicate rows can overstate the importance of repeated examples, distort
    class balance, and lead to optimistic evaluation metrics when duplicated
    samples leak into both train and validation splits.

    This function counts fully duplicated rows using :meth:`pandas.DataFrame.duplicated`
    and emits a concise console message.

    Parameters
    ----------
    df:
        The DataFrame to inspect.

    Returns
    -------
    bool
        ``True`` when duplicates are present, otherwise ``False``.

    Best practices
    --------------
    * Remove exact duplicates before splitting data.
    * Consider key-based deduplication if rows can differ in non-essential fields.
    * Audit pipeline joins and ingestion logic to prevent re-introducing duplicates.
    """

    duplicate_rows = int(df.duplicated().sum())
    if duplicate_rows:
        print(f"[Duplicates] {duplicate_rows} duplicated rows detected.")
        return True
    print("[Duplicates] None.")
    return False


def _check_constant_columns(df: pd.DataFrame) -> bool:
    """Detect columns that have no variation.

    Constant (zero-variance) columns carry no predictive signal. They increase
    feature dimensionality without adding information and may interfere with
    certain preprocessing steps or model diagnostics.

    A column is treated as constant when it has one unique value or less,
    including cases where all entries are missing.

    Parameters
    ----------
    df:
        The DataFrame to inspect.

    Returns
    -------
    bool
        ``True`` when at least one constant column exists, otherwise ``False``.

    Recommendations
    ---------------
    * Drop constant columns early in feature engineering.
    * Track removed columns to ensure reproducibility between training and
      inference environments.
    """

    constant_count = int((df.nunique(dropna=False) <= 1).sum())
    if constant_count:
        print(f"[Constant Columns] {constant_count} detected.")
        return True
    print("[Constant Columns] None.")
    return False


def _check_infinite(df: pd.DataFrame) -> bool:
    """Check numeric columns for positive or negative infinity.

    Infinite values often appear after unsafe arithmetic operations (division by
    zero, log of zero without clipping, overflow). Most estimators and scalers
    expect finite numeric input, so inf values can cause hard failures or unstable
    gradients.

    This helper inspects only numeric columns and reports how many columns contain
    at least one infinite value.

    Parameters
    ----------
    df:
        The DataFrame to inspect.

    Returns
    -------
    bool
        ``True`` when infinite values are found, otherwise ``False``.

    Mitigation guidance
    -------------------
    * Replace inf values with NaN, then apply a deliberate missing-data strategy.
    * Add guards around feature computations (denominator clipping, epsilon terms).
    * Validate transformed features as part of pipeline unit tests.
    """

    numeric_df = df.select_dtypes(include=[np.number])
    if numeric_df.empty:
        print("[Infinite Values] None.")
        return False

    infinite_cols = int(np.isinf(numeric_df.to_numpy()).any(axis=0).sum())
    if infinite_cols:
        print(f"[Infinite Values] Found in {infinite_cols} columns.")
        return True
    print("[Infinite Values] None.")
    return False


def _check_object_dtypes(df: pd.DataFrame) -> bool:
    """Identify columns stored with ``object`` dtype.

    Object dtype columns often indicate raw categorical text, mixed types, or
    values that were not parsed correctly. In ML pipelines, leaving these columns
    untreated can cause estimator errors, inconsistent encoding behavior, and
    hidden type coercion bugs.

    Parameters
    ----------
    df:
        The DataFrame to inspect.

    Returns
    -------
    bool
        ``True`` when one or more object-typed columns are present, otherwise
        ``False``.

    Practical guidance
    ------------------
    * Convert true categories to ``category`` or encode explicitly.
    * Parse numeric-like strings into numeric dtype where appropriate.
    * Keep schema contracts and enforce dtypes at data-ingestion boundaries.
    """

    object_cols = int((df.dtypes == "object").sum())
    if object_cols:
        print(f"[Object Dtype Columns] {object_cols} detected.")
        return True
    print("[Object Dtype Columns] None.")
    return False


def validate(df: pd.DataFrame) -> bool:
    """Run a compact, production-friendly validation pass over a DataFrame.

    This function provides a pragmatic first-line quality gate for tabular data
    used in machine-learning and analytics workflows. It executes five targeted
    checks that frequently uncover data issues before model training:

    1. Missing values
    2. Duplicate rows
    3. Constant columns
    4. Infinite values
    5. Object dtype columns

    Each check prints a **short, clean console message** so the output remains
    readable in notebooks, scripts, and CI logs. The function then returns a
    boolean status indicating whether the dataset passed all checks.

    Why these checks matter
    -----------------------
    **Missing values** can break estimators, skew statistics, and reduce training
    signal when rows are dropped indiscriminately.

    **Duplicate rows** can overweight repeated samples, artificially inflate
    confidence in model metrics, and create leakage-like effects if duplicated
    examples cross train/validation boundaries.

    **Constant columns** add no predictive value, increase feature-space noise,
    and can complicate feature importance interpretation.

    **Infinite values** are typically symptoms of unstable feature engineering
    operations (for example, division by zero) and can cause numerical failures.

    **Object dtype columns** often indicate unresolved schema issues that require
    explicit encoding or parsing before most ML models can consume them safely.

    Impact on model performance and reliability
    -------------------------------------------
    When these problems remain unresolved, models may fail during fit, converge
    poorly, overfit due to distorted distributions, or produce non-reproducible
    behavior across environments. Early validation improves pipeline robustness,
    reduces debugging time, and helps enforce data contracts between data
    preparation and modeling stages.

    Best-practice remediation workflow
    ----------------------------------
    * Run ``validate`` immediately after loading raw data.
    * Triage reported issues by severity and business context.
    * Apply deterministic cleaning steps (imputation, deduplication, type casting,
      feature filtering) in version-controlled preprocessing code.
    * Re-run validation after transformations and before model training.
    * Persist schema expectations (column names, dtypes, ranges) so drift can be
      detected automatically.

    Parameters
    ----------
    df:
        Input pandas DataFrame to validate.

    Returns
    -------
    bool
        ``True`` when no issues are detected across all checks; ``False`` when
        one or more checks report problems.

    Raises
    ------
    TypeError
        If ``df`` is not a pandas DataFrame.

    Examples
    --------
    >>> import pandas as pd
    >>> from sklean import validate
    >>> data = pd.DataFrame({"x": [1, 2, 2], "y": ["a", "b", "b"]})
    >>> validate(data)
    [Missing Values] None.
    [Duplicates] 1 duplicated rows detected.
    [Constant Columns] None.
    [Infinite Values] None.
    [Object Dtype Columns] 1 detected.
    False
    """

    if not isinstance(df, pd.DataFrame):
        raise TypeError("validate expects a pandas.DataFrame")

    checks = (
        _check_missing(df),
        _check_duplicates(df),
        _check_constant_columns(df),
        _check_infinite(df),
        _check_object_dtypes(df),
    )
    return not any(checks)


if __name__ == "__main__":
    demo = pd.DataFrame(
        {
            "feature": [1.0, np.inf, 1.0],
            "label": ["yes", "yes", "yes"],
            "score": [0.5, np.nan, 0.5],
        }
    )
    print(f"Validation passed: {validate(demo)}")
