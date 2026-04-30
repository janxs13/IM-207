"""
Seat layout generator — supports 2, 3, 4, 5 column layouts.
Generates seat IDs in the format A1, B1, C1 etc.
"""

LAYOUT_COLUMNS = {
    "2-column": (["A"], ["B"]),
    "3-column": (["A", "B"], ["C"]),
    "4-column": (["A", "B"], ["C", "D"]),
    "5-column": (["A", "B"], ["C", "D", "E"]),
}


def generate_seat_layout(total_seats: int, layout: str = "4-column") -> list:
    layout = (layout or "4-column").lower()
    left_cols, right_cols = LAYOUT_COLUMNS.get(layout, LAYOUT_COLUMNS["4-column"])
    all_cols     = left_cols + right_cols
    seats_per_row = len(all_cols)
    rows         = (total_seats + seats_per_row - 1) // seats_per_row

    seats = []
    for r in range(1, rows + 1):
        for col in all_cols:
            if len(seats) < total_seats:
                seats.append(f"{col}{r}")
    return seats


def get_layout_config(layout: str) -> dict:
    """Return metadata for a given layout type."""
    layout = (layout or "4-column").lower()
    left_cols, right_cols = LAYOUT_COLUMNS.get(layout, LAYOUT_COLUMNS["4-column"])
    return {
        "left_cols":      left_cols,
        "right_cols":     right_cols,
        "seats_per_row":  len(left_cols) + len(right_cols),
        "layout":         layout,
    }
