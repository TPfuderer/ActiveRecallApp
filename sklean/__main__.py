"""Runnable example for the sklean package."""

import numpy as np
import pandas as pd

from . import validate


if __name__ == "__main__":
    demo = pd.DataFrame(
        {
            "feature": [1.0, np.inf, 1.0],
            "label": ["yes", "yes", "yes"],
            "score": [0.5, np.nan, 0.5],
        }
    )
    print(f"Validation passed: {validate(demo)}")
