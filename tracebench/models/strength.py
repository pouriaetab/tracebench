"""Model S: is a level getting stronger or weaker?

Each time price tests a level it either breaks through or holds: a Bernoulli
trial. Split the level's tests into an earlier half and a recent half. With a
Beta(1, 1) prior on each half's break probability, the posterior after b breaks
and h holds is Beta(1 + b, 1 + h) (the Beta-Binomial conjugate update).

The signal is the posterior probability that the recent break rate is LOWER
than the earlier one, estimated by drawing from both posteriors:

    p = P(theta_recent < theta_earlier | data)

p >= threshold -> "strengthening", p <= 1 - threshold -> "weakening", else
"holding". With too few tests per half the answer is "forming" (not enough
evidence), never a label.

Threshold. The original design used 0.75. Validation (VAL-S1) showed that at
0.75 a level whose break rate has NOT changed is called "strengthening" 19 to
27 percent of the time, against a requirement of at most 10 percent (S-5). That
is known issue KI-1. The default is now 0.95, which meets S-5 at every sample
size tested; the price is lower power on small samples, which the validation
report states (S-6).
"""
from __future__ import annotations

import numpy as np

PRIOR_ALPHA = 1.0
PRIOR_BETA = 1.0
MC_SAMPLES = 20_000
THRESHOLD = 0.95            # adopted after VAL-S1 (change CR-1)
INHERITED_THRESHOLD = 0.75  # the original design, fails S-5 (KI-1)
MIN_TESTS_PER_HALF = 4
SEED = 0


def posterior(breaks: int, holds: int, a0: float = PRIOR_ALPHA,
              b0: float = PRIOR_BETA) -> tuple[float, float]:
    if breaks < 0 or holds < 0:
        raise ValueError("counts must be non-negative")
    return a0 + breaks, b0 + holds


def posterior_mean(a: float, b: float) -> float:
    return a / (a + b)


def credible_interval(a: float, b: float, cred: float = 0.9, samples: int = MC_SAMPLES,
                      seed: int = SEED) -> tuple[float, float]:
    draws = np.random.default_rng(seed).beta(a, b, size=samples)
    lo = (1.0 - cred) / 2.0
    return float(np.quantile(draws, lo)), float(np.quantile(draws, 1.0 - lo))


def prob_break_rate_fell(recent: tuple[float, float], earlier: tuple[float, float],
                         samples: int = MC_SAMPLES, seed: int = SEED) -> float:
    rng = np.random.default_rng(seed)
    r = rng.beta(recent[0], recent[1], size=samples)
    e = rng.beta(earlier[0], earlier[1], size=samples)
    return float(np.mean(r < e))


def classify(p_fell: float, threshold: float = THRESHOLD) -> str:
    if p_fell >= threshold:
        return "strengthening"
    if p_fell <= 1.0 - threshold:
        return "weakening"
    return "holding"


def assess(outcomes: list[int], threshold: float = THRESHOLD, samples: int = MC_SAMPLES,
           seed: int = SEED) -> tuple[str, float | None]:
    """outcomes: 1 = broke, 0 = held, oldest first. Returns (label, p_fell)."""
    half = len(outcomes) // 2
    if half < MIN_TESTS_PER_HALF:
        return "forming", None
    earlier, recent = outcomes[:half], outcomes[len(outcomes) - half:]
    pe = posterior(sum(earlier), len(earlier) - sum(earlier))
    pr = posterior(sum(recent), len(recent) - sum(recent))
    p = prob_break_rate_fell(pr, pe, samples, seed)
    return classify(p, threshold), p


def hyperparameters() -> dict:
    return {"prior": (PRIOR_ALPHA, PRIOR_BETA), "mc_samples": MC_SAMPLES,
            "threshold": THRESHOLD, "min_tests_per_half": MIN_TESTS_PER_HALF}
