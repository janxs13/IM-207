def generate_seats(total=40):

    seats = []

    rows = total // 4

    for r in range(1, rows + 1):

        seats.append(f"A{r}")
        seats.append(f"B{r}")
        seats.append(f"C{r}")
        seats.append(f"D{r}")

    return seats