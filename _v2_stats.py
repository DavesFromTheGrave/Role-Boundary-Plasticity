"""Read-only stats helper for PAPER v2. Wilson CIs + two-sided Fisher exact.
Feeds on canonical k/n already produced by _insight_pass.py. Prints only."""
import math

Z = 1.959963984540054  # 95%


def wilson(k, n):
    if n == 0:
        return (None, None, None)
    p = k / n
    d = 1 + Z * Z / n
    c = p + Z * Z / (2 * n)
    h = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n))
    return (round(100 * p, 1), round(100 * (c - h) / d, 1), round(100 * (c + h) / d, 1))


def fisher_two_sided(k1, n1, k2, n2):
    # 2x2: [[k1, n1-k1], [k2, n2-k2]]
    a, b, c, d = k1, n1 - k1, k2, n2 - k2
    row1, row2 = a + b, c + d
    col1, col2 = a + c, b + d
    tot = a + b + c + d

    def logp(x):
        # hypergeometric prob of a=x
        return (math.lgamma(row1 + 1) + math.lgamma(row2 + 1) +
                math.lgamma(col1 + 1) + math.lgamma(col2 + 1) -
                math.lgamma(tot + 1) - math.lgamma(x + 1) -
                math.lgamma(row1 - x + 1) - math.lgamma(col1 - x + 1) -
                math.lgamma(x + row2 - col1 + 1))

    lo = max(0, col1 - row2)
    hi = min(row1, col1)
    p_obs = logp(a)
    tot_p = 0.0
    for x in range(lo, hi + 1):
        lp = logp(x)
        if lp <= p_obs + 1e-9:
            tot_p += math.exp(lp)
    return tot_p


CIS = [
    ("cloud L2 polite", 87, 98),
    ("cloud L3 shouty", 40, 99),
    ("cloud L3_notags control", 36, 99),
    ("cloud generic forgery", 64, 99),
    ("cloud forged pooled (6 syn)", 283, 592),
    ("cot forged_llama3 (user delim)", 146, 288),
    ("cot L3_notags", 119, 288),
    ("cot think_forged", 70, 282),
    ("cot think_forged_destyled", 62, 286),
    ("cot refund think_forged", 26, 123),
    ("cot refund destyled", 27, 126),
    ("main tool_result channel", 1230, 2145),
    ("cloud tool_result channel", 551, 1083),
]

TESTS = [
    ("cloud L2 vs L3 (politeness inversion)", 87, 98, 40, 99),
    ("cloud generic forgery vs notags control", 64, 99, 36, 99),
    ("cloud forged pooled vs notags control", 283, 592, 36, 99),
    ("cot user-delim forgery vs think forgery", 146, 288, 70, 282),
    ("cot think_forged vs think_destyled (Ye et al. ablation)", 70, 282, 62, 286),
    ("cot user-delim forgery vs L3_notags", 146, 288, 119, 288),
    ("deepseek-v4-pro forged pooled vs notags", 23, 36, 0, 6),
]

print("WILSON 95% CIs")
print("-" * 66)
for label, k, n in CIS:
    p, lo, hi = wilson(k, n)
    print(f"{label:38s} {k:>4}/{n:<4}  {p:>5}%  [{lo}, {hi}]")

print()
print("TWO-SIDED FISHER EXACT")
print("-" * 66)
for label, k1, n1, k2, n2 in TESTS:
    p = fisher_two_sided(k1, n1, k2, n2)
    print(f"{label:52s}  p = {p:.3g}")
