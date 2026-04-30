"""Alias module for backward compatibility."""
from utils.seat_layout_generator import generate_seat_layout, get_layout_config


def generate_seats(total: int = 40, layout: str = "4-column") -> list:
    return generate_seat_layout(total, layout)
