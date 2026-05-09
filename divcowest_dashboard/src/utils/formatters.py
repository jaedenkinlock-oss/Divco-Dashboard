def fmt_currency(val, decimals: int = 2) -> str:
    if val is None or val != val:
        return "—"
    return f"${val:,.{decimals}f}"


def fmt_large(val) -> str:
    """Format large numbers: 1.2B, 450M, etc."""
    if val is None or val != val:
        return "—"
    if abs(val) >= 1e12:
        return f"${val/1e12:.2f}T"
    if abs(val) >= 1e9:
        return f"${val/1e9:.2f}B"
    if abs(val) >= 1e6:
        return f"${val/1e6:.1f}M"
    return f"${val:,.0f}"


def fmt_pct(val, decimals: int = 2) -> str:
    if val is None or val != val:
        return "—"
    return f"{val * 100:.{decimals}f}%"


def fmt_multiple(val, decimals: int = 1) -> str:
    if val is None or val != val:
        return "—"
    return f"{val:.{decimals}f}x"


def fmt_bps(val) -> str:
    if val is None or val != val:
        return "—"
    return f"{int(round(val * 10000))} bps"
