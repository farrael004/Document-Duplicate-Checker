def longest_common_substring(s1, s2):
    """
    This function currently is not used, but could be useful for displaying \
    what parts of the documents overlap with one another. However, it might \
    prove challenging to implement this in case there are multiple documents \
    in a cluster.
    """
    m = [[0] * (1 + len(s2)) for _ in range(1 + len(s1))]
    longest, x_longest = 0, 0
    for x in range(1, 1 + len(s1)):
        for y in range(1, 1 + len(s2)):
            if s1[x - 1] == s2[y - 1]:
                m[x][y] = m[x - 1][y - 1] + 1
                if m[x][y] > longest:
                    longest = m[x][y]
                    x_longest = x
            else:
                m[x][y] = 0
    return s1[x_longest - longest: x_longest]


def find_reocurring_string(strings: list[str]):
    common_substrings = set(strings[0])

    for string in strings[1:]:
        new_common_substrings = set()
        for common_substring in common_substrings:
            new_common_substrings.add(longest_common_substring(common_substring, string))
        common_substrings = new_common_substrings