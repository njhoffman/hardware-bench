"""Percentile of a score among OpenBenchmarking.org results.

The suite's percentile data is 100 cut points, ascending: cut i is the result
at i% of the sorted samples. The rank follows the suite's ob_auto_compare
module, so both report the same number: higher-is-better scores get the index
of the first cut above them minus one, lower-is-better scores 100 minus it.
"""


def cut_points(raw):
    """100 numbers from the suite's list, or a dict keyed by index."""
    if isinstance(raw, dict):
        raw = [raw[k] for k in sorted(raw, key=int)]
    return [float(v) for v in raw or ()]


def rank(value, cuts, hib=True):
    """Percentile 0-100 of value among cuts, or None without data."""
    if value is None or not cuts:
        return None
    for i, v in enumerate(cuts):
        if v > value:
            return max(0, min(100, i - 1 if hib else 100 - i))
    return 99 if hib else 0


def ordinal(n):
    if n is None:
        return '-'
    n = int(n)
    suffix = 'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f'{n}{suffix}'


def summarize(tests):
    """Mean percentile per component and overall (mean of the components)."""
    by = {}
    for t in tests:
        if t.get('percentile') is not None:
            by.setdefault(t['component'], []).append(t['percentile'])
    out = {c: round(sum(v) / len(v)) for c, v in by.items()}
    if out:
        out['overall'] = round(sum(out.values()) / len(out))
    return out
