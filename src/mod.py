def page(items, n, size):
    start = n * size
    return items[start:start + size]
