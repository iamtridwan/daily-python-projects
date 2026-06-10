messy_names = [
    "  alice ", "Bob", " charlie", "Alice", "BOB ", "eve  ", " Eve", "eve"]

def clean_names(names):
    """Cleans a list of names."""
    return sorted(list(set([name.strip().title() for name in names])))


if __name__ == '__main__':
    print("Messy names:", messy_names)
    print("Cleaned and Sorted names:", clean_names(messy_names))
    print('************************************')