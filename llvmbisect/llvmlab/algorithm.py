"""Handy algorithms."""


def bisect(predicate, list):
    """
    bisect(predicate, list) -> item or None

    Given a test predicate and a list of items, search return the first item in
    the list for which the predicate succeeds, or None if no such item is
    found.

    The list is assumed to be ordered such that (predicate(i) for i in list) is
    monotonic. If this condition is not met, the returned item is guaranteed to
    satisfy the predicate and the item preceeding it is guaranteed to fail the
    predicate, but that is all. Additionally, if the last item does not pass
    the predicate, such an item might not be found.

    This function is optimized for the case where the searched for item is near
    the beginning of the list.
    """

    if not list:
        return None

    lo = 0
    hi = len(list)-1

    # Check first item immediately.
    if predicate(list[lo]):
        return list[lo]

    # Invariants:
    #  not predicate(list[lo])
    #  predicate(list[hi])

    # Binary search region.
    while lo + 1 != hi:
        mid = (lo + hi) // 2
        if predicate(list[mid]):
            hi = mid
        else:
            lo = mid

    return list[hi]


def gallop(predicate, list):
    """
    gallop(predicate, list) -> list or None

    Given a test predicate and a list of items, reduce the search space
    assuming the searched for item is near the beginning of the list.

    The list is assumed to be ordered such that (predicate(i) for i in list) is
    monotonic. If this condition is not met, the returned item is guaranteed to
    satisfy the predicate and the item preceeding it is guaranteed to fail the
    predicate, but that is all. Additionally, if the last item does not pass
    the predicate, such an item might not be found.
    """

    if not list:
        return None

    # Check first item immediately.
    if predicate(list[0]):
        return list[0:1]

    # Invariants:
    #  not predicate(list[lo])

    # Gallop to find initial search range, under the assumption that we are
    # most likely looking for something at the head of this list.
    lo = 0
    hi = 1
    while hi < len(list):
        if predicate(list[hi]):
            break
        lo, hi = hi, hi + (hi - lo)*2

    # If we galloped past the end, limit the hi range.
    if hi >= len(list):
        hi = len(list) - 1
        if hi == lo or not predicate(list[hi]):
            return None
    return list[lo:hi+1]
