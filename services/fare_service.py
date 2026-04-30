"""
LTFRB Fare Matrix Service
Philippine Land Transportation Franchising & Regulatory Board
Official fare guidelines for provincial buses.

Reference: LTFRB MC 2023-009 (latest fare adjustment)
"""

# ── LTFRB Base Fares (PHP) ────────────────────────────────
LTFRB_FARES = {
    "ordinary":  {"base_fare": 13.00, "base_km": 5, "per_km": 2.20},
    "aircon":    {"base_fare": 15.00, "base_km": 5, "per_km": 2.65},
    "provincial": {"base_fare": 13.00, "base_km": 5, "per_km": 2.20},
    "tourist":   {"base_fare": 17.00, "base_km": 5, "per_km": 3.00},
}

# ── Discount rates per RA ─────────────────────────────────
# RA 9994 (Senior Citizens Act) + RA 7277 (PWD Act)
DISCOUNT_RATES = {
    "senior":  0.20,   # 20% — RA 9994
    "pwd":     0.20,   # 20% — RA 7277
    "student": 0.00,   # No national mandate (LGU-specific)
    "regular": 0.00,
}

# ── VAT Exemption ─────────────────────────────────────────
# Senior and PWD passengers are VAT-exempt per their respective laws
VAT_EXEMPT_TYPES = {"senior", "pwd"}
VAT_RATE = 0.12


def compute_ltfrb_fare(
    distance_km: float,
    bus_type: str = "ordinary",
    passenger_type: str = "regular"
) -> dict:
    """
    Compute fare based on LTFRB matrix.
    Returns a dict with breakdown for display on ticket.
    """
    bus_type = (bus_type or "ordinary").lower()
    passenger_type = (passenger_type or "regular").lower()
    config = LTFRB_FARES.get(bus_type, LTFRB_FARES["ordinary"])

    base_fare  = config["base_fare"]
    base_km    = config["base_km"]
    per_km     = config["per_km"]
    extra_km   = max(0.0, float(distance_km) - base_km)
    gross_fare = round(base_fare + (extra_km * per_km), 2)

    discount_rate   = DISCOUNT_RATES.get(passenger_type, 0.0)
    discount_amount = round(gross_fare * discount_rate, 2)
    net_fare        = round(gross_fare - discount_amount, 2)

    # VAT exemption for senior/PWD
    vat_amount = 0.0
    if passenger_type not in VAT_EXEMPT_TYPES:
        vat_amount = round(net_fare * VAT_RATE / (1 + VAT_RATE), 2)  # VAT-inclusive

    return {
        "distance_km":      round(float(distance_km), 1),
        "bus_type":         bus_type,
        "passenger_type":   passenger_type,
        "base_fare":        base_fare,
        "gross_fare":       gross_fare,
        "discount_type":    passenger_type if discount_rate > 0 else None,
        "discount_rate":    discount_rate,
        "discount_amount":  discount_amount,
        "vat_amount":       vat_amount,
        "final_fare":       net_fare,
        "is_vat_exempt":    passenger_type in VAT_EXEMPT_TYPES,
        "ltfrb_compliant":  True,
    }


def apply_discount_to_fare(fare: float, passenger_type: str) -> dict:
    """
    Apply discount to a fixed fare (admin-set price).
    Used when the fare is already set and we just need to apply the discount.
    """
    passenger_type = (passenger_type or "regular").lower()
    discount_rate   = DISCOUNT_RATES.get(passenger_type, 0.0)
    discount_amount = round(fare * discount_rate, 2)
    final_fare      = round(fare - discount_amount, 2)

    return {
        "original_fare":    fare,
        "passenger_type":   passenger_type,
        "discount_type":    passenger_type if discount_rate > 0 else None,
        "discount_rate":    discount_rate,
        "discount_amount":  discount_amount,
        "final_fare":       final_fare,
        "is_vat_exempt":    passenger_type in VAT_EXEMPT_TYPES,
    }
