import itertools as it
import re
from itertools import combinations
from math import ceil
from urllib.parse import parse_qs, urlencode, urlparse

import quickbolt.utils.dictionary as dh
import quickbolt.utils.json as jh


def generate_batch(
    method: str,
    url: str,
    description: str = "",
    headers: None | dict = None,
    json: None | dict = None,
    data: None | dict = None,
    bad_header_count: int = 1,
    unsafe_bodies: bool = False,
    corrupt_query_params: bool = True,
    min: bool = True,
    corrupt_keys: bool = False,
) -> list[dict]:
    """
    This generates url batches to feed into the aio_requests.request loader.

    Args:
        method: The method of the request.
        url: A 200 type url(a passing request).
        description: A description of the request.
        headers: The headers of the request.
        json: A json (dict) body of the request.
        data: A data (dict) body of the request.
        bad_header_count: The amount of bad header possibilities used.
        unsafe_bodies: Whether to include unsafe bodies in the batch.
        corrupt_query_params: Whether to corrupt the query params.
        min: Whether to give the minimum amount of corruptions.
        corrupt_keys: Whether to corrupt the keys of a data set.

    Returns:
        batch: The list of 200-500 request corruptions.
    """
    method = method.lower()
    good_code = {
        "get": "200",
        "patch": "200",
        "post": "201",
        "put": "204",
        "delete": "204",
    }[method]

    headers = headers or {}
    bad_headers = []
    if headers:
        bad_headers = generate_bad_bodies(headers, min=min)[:bad_header_count]

    invalid_sub_values = {"str": "aaa", "digit": "999"}
    invalid_urls = generate_bad_urls(url, invalid_sub_values, corrupt_query_params, min)
    not_found_urls = generate_bad_urls(
        url, corrupt_query_params=corrupt_query_params, min=min
    )

    clean_url = url.replace(";", "")
    if description:
        description += " "

    batch = [
        *[
            {
                "code": good_code,
                "description": f"{description}good",
                "method": method,
                "headers": headers,
                "url": clean_url,
            }
        ],
        *[
            {
                "code": "400",
                "description": f"{description}invalid",
                "method": method,
                "headers": headers,
                "url": u,
            }
            for u in invalid_urls
        ],
        *[
            {
                "code": "401",
                "description": f"{description}not auth",
                "method": method,
                "headers": h,
                "url": clean_url,
            }
            for h in bad_headers
        ],
        *[
            {
                "code": "404",
                "description": f"{description}not found",
                "method": method,
                "headers": headers,
                "url": u,
            }
            for u in not_found_urls
        ],
    ]

    if json or data:
        body = json
        key = "json"
        if data:
            body = data
            key = "data"

        for b in batch:
            b[key] = body

        good_batch = {
            "code": good_code,
            "description": f"{description}good",
            "method": method,
            "headers": headers,
            "url": clean_url,
        }

        bad_bodies_batch = [
            *[
                {
                    **good_batch,
                    **{key: b, "description": f"{description}invalid"},
                    "code": "400",
                }
                for b in generate_bad_bodies(
                    body, invalid_sub_values, min=min, corrupt_keys=corrupt_keys
                )
            ],
            *[
                {
                    **good_batch,
                    **{key: b, "description": f"{description}not found"},
                    "code": "404",
                }
                for b in generate_bad_bodies(body, min=min, corrupt_keys=corrupt_keys)
            ],
        ]

        if unsafe_bodies:
            extra_batch = [
                {
                    **good_batch,
                    **{key: b, "description": f"{description}unsafe bodies"},
                    "code": "???",
                }
                for b in generate_unsafe_bodies(body)
            ]
            bad_bodies_batch.extend(extra_batch)

        batch.extend(bad_bodies_batch)
        batch.sort(key=lambda k: k["code"].split("|")[0])

    return batch


def generate_bad_urls(
    url: str,
    sub_values: None | dict = None,
    corrupt_query_params: bool = True,
    min: bool = True,
) -> list:
    """
    This generates a list of bad urls e.g. path params and query params.

    Args:
        data: A 200 type url.
        sub_values: Regex type substitutes for char type replacements.
        corrupt_query_params: Whether to corrupt the query params.
        min: Whether to give the minimum amount of corruptions.

    Returns:
        bad_urls: The list of bad urls for the request.
    """
    parsed = urlparse(url)

    query = parsed.query
    query_dict = {"query": parse_qs(query) or ""}

    marked_url = url
    path = parsed.path
    if ";" not in parsed.path:
        marked_path = f";{path}"
        marked_url = marked_url.replace(path, marked_path)
        path = marked_path

    _, params = path.split(";")
    params_split = params.lstrip("/").split("/")
    params_keys = [f"{p}_{i}" for i, p in enumerate(params_split)]

    corruptables = {"params": dict(zip(params_keys, params_split))}
    if corrupt_query_params:
        corruptables.update(query_dict)
    corruptables = dh.flatten(corruptables)
    corruptables_ser = jh.serialize(corruptables)

    bad_combos_des = generate_bad_data(corruptables_ser, corruptables, sub_values, min)
    bad_combos_unfl = [dh.unflatten(b) for b in bad_combos_des]

    bad_urls = []
    clean_url = url.replace(";", "")
    base_url = marked_url.split(";")[0].lstrip("/").rstrip("/")
    for bad_combo in bad_combos_unfl:
        query = bad_combo.get("query", "") or query_dict.get("query", "")
        if query:
            query = urlencode(query, doseq=True)
            query = f"?{query}"

        params = bad_combo.get("params", "")
        if params:
            params = "/".join(params.values()).rstrip("/")

        bad_url = f"{base_url}/{params + query}"
        if bad_url != clean_url:
            bad_urls.append(bad_url)

    return list(dict.fromkeys(bad_urls))


def generate_bad_bodies(
    data: dict,
    sub_values: None | dict = None,
    min: bool = True,
    corrupt_keys: bool = False,
) -> list[dict]:
    """
    This generates a list of bad bodies.

    Args:
        data: A 200 type body.
        sub_values: Regex type substitutes for char type replacements.
        min: Whether to give the minimum amount of corruptions.
        corrupt_keys: Whether to corrupt the keys of a data set.

    Returns:
        bad_data: The unflattened list of bad data for the request.
    """
    data_copy_flat = dh.flatten(data)

    corruptables = {}
    incorruptibles = {}
    for key, value in data_copy_flat.items():
        if "file" in key or not isinstance(value, (int, float, str)):
            incorruptibles[key] = value
        else:
            corruptables[key] = value
    data_copy_flat_ser = jh.serialize(corruptables)

    bad_combos_des = generate_bad_data(
        data_copy_flat_ser, corruptables, sub_values, min, corrupt_keys
    )

    if incorruptibles:
        for bad_combo in bad_combos_des:
            bad_combo.update(incorruptibles)

    bad_combos_unfl = [dh.unflatten(b) for b in bad_combos_des]

    seen = []
    unique_dicts = []
    for bad_combo in bad_combos_unfl:
        t = tuple(bad_combo.items())
        if t not in seen:
            unique_dicts.append(bad_combo)
            seen.append(t)

    return unique_dicts


def generate_bad_data(
    data_flat_ser: str,
    corruptables: dict,
    sub_values: dict,
    min: bool = True,
    corrupt_keys: bool = False,
) -> list[dict]:
    """
    This creates the corrupted combinations.

    Args:
        data_flat_ser: A flat, serialized version of the data being corrupted.
        corruptables: The values to target for corruption.
        sub_values: Regex type substitutes for char type replacements.
        min: Whether to give the minimum amount of corruptions.
        corrupt_keys: Whether to corrupt the keys of a data set.

    Returns:
        bad_combos_des: The list of deserialized bad data for the request.
    """

    def corruption_regex(value_str, active_sub_values):
        corrupt_value = value_str

        str_sub = active_sub_values.get("str")
        if str_sub:
            corrupt_value = re.sub(r"[a-zA-Z]", str_sub, corrupt_value)

        digit_sub = active_sub_values.get("digit")
        if digit_sub:
            corrupt_value = re.sub(r"\d", digit_sub, corrupt_value)

        return corrupt_value

    active_sub_values = {"str": "a", "digit": "0"}
    if isinstance(sub_values, dict):
        active_sub_values.update(sub_values)

    num_of_combos = 1
    if not min:
        num_of_combos = ceil(len(corruptables) / 3)

    combos = list(combinations(corruptables.items(), num_of_combos))
    combos.append(tuple(corruptables.items()))

    bad_combos = []
    for combo in combos:
        bad_combo_value = data_flat_ser
        bad_combo_key = data_flat_ser

        for key, value in combo:
            key_str = f'"{key}"'

            if isinstance(value, str):
                value_str = f'"{value}"'
            else:
                value_str = str(value)

            corrupt_value = corruption_regex(value_str, active_sub_values)
            bad_combo_value = bad_combo_value.replace(
                f"{key_str}: {value_str}", f"{key_str}: {corrupt_value}"
            )

            corrupt_key = None
            if corrupt_keys and len(corruptables) != len(combo):
                corrupt_key = corruption_regex(key_str, {"str": "a"})
                bad_combo_key = bad_combo_key.replace(
                    f"{key_str}: {value_str}", f"{corrupt_key}: {value_str}"
                )

        bad_combos.append(bad_combo_value)
        if corrupt_keys and corrupt_key:
            bad_combos.append(bad_combo_key)

    return [jh.deserialize(b) for b in bad_combos]


def generate_unsafe_bodies(body: dict) -> list[dict]:
    """
    This creates an unsafe body from a good one.

    Args:
        body: The body to be corrupted.

    Returns:
        bad_bodies: The unsafe bodies.
    """
    conditions = [
        " '--",
        "'+OR+1=1--",
        "' and substr(version(),1,10) = 'PostgreSQL' and '1  -> OK",
    ]
    queries = [
        "SELECT version() --",
        "select database_to_xml(true,true,'');",
        "UNION SELECT * FROM information_schema.tables --",
    ]
    germs = conditions + queries

    num_combinations = len(body)
    combinations = [
        c
        for c in it.combinations(germs, num_combinations)
        if len(set([i[0] for i in c])) > num_combinations - 1
    ]

    return [
        {k: f"{v} {p}" for k, v in body.items() if "file" not in k}
        for c in combinations
        for p in c
    ]
