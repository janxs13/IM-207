def generate_seat_layout(total_seats):

    seats = []

    rows = total_seats // 4

    for r in range(1, rows + 1):

        seats.append(f"A{r}")
        seats.append(f"B{r}")
        seats.append(f"C{r}")
        seats.append(f"D{r}")

    return seats