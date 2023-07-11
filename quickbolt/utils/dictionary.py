import re


def flatten(d: dict | list) -> dict:
    """
    This flattens a nested dictionary.

    Args:
        d: The object to flatten.

    Returns:
        flat_d: The flattened object.
    """

    def recurse(value, parent_key=""):
        if isinstance(value, list):
            if not value:
                obj[parent_key] = value
            else:
                for i, v in enumerate(value):
                    recurse(v, f"{parent_key}.{i}" if parent_key else str(i))
        elif isinstance(value, dict):
            if not value:
                obj[parent_key] = value
            else:
                for k, v in value.items():
                    recurse(v, f"{parent_key}.{k}" if parent_key else k)
        else:
            obj[parent_key] = value

    obj = {}
    recurse(d)
    return obj


def unflatten(flat_dict: dict) -> dict | list:
    """
    This unflattens a flattened dictionary.

    Args:
        flat_dict: The flat dictionary to unflatten.

    Returns:
        unflattened_dict: The unflattened dict.
    """

    def assign(keys, value, d):
        key = keys.pop(0)

        if key.isdigit():
            key = int(key)
            if isinstance(d, dict):
                d = [d]
            while len(d) <= key:
                d.append(None)
        else:
            if isinstance(d, list):
                d[-1] = {}

        if len(keys) == 0:
            d[key] = value
        else:
            if isinstance(d, list):
                d[key] = assign(
                    keys, value, d[key] if key < len(d) and d[key] is not None else {}
                )
            else:
                d[key] = assign(
                    keys, value, d.get(key, [{}] if keys[0].isdigit() else {})
                )

        return d

    if len(flat_dict) == 1 and "" in flat_dict:
        return flat_dict[""]

    unflattened = {}
    for flat_key, value in flat_dict.items():
        keys = flat_key.split(".")
        unflattened = assign(keys, value, unflattened)

    return unflattened


def compare_dictionaries(
    d1: dict,
    d2: dict,
    skipped_keys: None | list = None,
    exclusive_keys: None | list = None,
    normalize: bool = False,
) -> dict:
    """
    This does a general key then value mismatch comparison of two dictionaries.

    Args:
        d1: The first dictionary to compare.
        d2: The second dictionary to compare.
        skipped_keys: The keys to skip in the comparison.
        exclusive_keys: The keys to exclusively check ignoring any skipped keys passed.
        normalize: Whether to convert each of the comparable values in the same casing.

    Returns:
        mismatches: The record of any key and value mismatches.
    """
    flat_d1 = flatten(d1)
    flat_d2 = flatten(d2)
    flat_d1_keys = set(flat_d1.keys())
    flat_d2_keys = set(flat_d2.keys())
    thin_keys = flat_d1_keys.union(flat_d2_keys)
    skipped_keys = skipped_keys or []

    if skipped_keys:
        _keys = [k for k in thin_keys if any(sk in k for sk in skipped_keys)]
        skipped_keys.extend(_keys)
    if exclusive_keys:
        _keys = [
            key for key in thin_keys if len(re.split("|".join(exclusive_keys), key)) < 2
        ]
        skipped_keys.extend(_keys)

    mismatches = {}
    f1_not_in_f2 = flat_d1_keys - set(skipped_keys) - flat_d2_keys
    f2_not_in_f1 = flat_d2_keys - set(skipped_keys) - flat_d1_keys
    mismatched_keys = list(f1_not_in_f2) + list(f2_not_in_f1)

    mismatched_skipped_keys = set(mismatched_keys).union(skipped_keys)
    if normalize:
        for k in set(flat_d1.keys()).union(flat_d2.keys()):
            if k not in mismatched_skipped_keys and isinstance(flat_d1.get(k), str):
                flat_d1[k] = flat_d1[k].lower()
            if k not in mismatched_skipped_keys and isinstance(flat_d2.get(k), str):
                flat_d2[k] = flat_d2[k].lower()

    mismatched_values = [
        {"key": k, "d1": v, "d2": flat_d2[k]}
        for k, v in flat_d1.items()
        if k not in mismatched_skipped_keys and v != flat_d2.get(k)
    ]

    if mismatched_keys:
        keys = {"f1_not_in_f2": list(f1_not_in_f2), "f2_not_in_f1": list(f2_not_in_f1)}
        mismatches["keys"] = [{k: v for k, v in keys.items() if v}]
    if mismatched_values:
        mismatches["values"] = mismatched_values
    if skipped_keys:
        mismatches["skipped_keys"] = skipped_keys

    return mismatches
