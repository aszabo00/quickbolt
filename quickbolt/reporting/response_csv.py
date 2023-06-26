import ast
import csv
import re

import aiofiles.os as aos
import numpy as np
from aiocsv import AsyncDictReader, AsyncReader, AsyncWriter
from aiofiles import open as aopen

import quickbolt.utils.json as jh


async def read_csv(csv_path: None | str) -> list[list]:
    """
    This reads a csv.

    Args:
        csv_path: The path to the csv file. If path is None the default one is found and used.
    Returns:
        data: The rows of a csv file.
    """
    async with aopen(csv_path, encoding="ascii", newline="") as csv_file:
        data = [row async for row in AsyncReader(csv_file)]

    return [
        [
            ast.literal_eval(item)
            if (
                not ("MultiDict" in item or "BufferedReader" in item)
                and ("[" in item or "{" in item)
            )
            else item
            for item in row
        ]
        for row in data
        if row
    ]


def scrub_field(data_message: str, field: str) -> str:
    """
    This scrubs a specific field for alphanumerical data.

    Args:
        data_message: The message to scrub.
        field: The field in the json to scrub.

    Returns:
        data_message: The scrubbed message.
    """
    data_dict = jh.deserialize(data_message)
    scrubbed_field = jh.serialize(data_dict[field])[:]

    targets = re.findall(
        r"([A-Za-z]+[\d@]+[\w@]*|[\d@]+[A-Za-z]+[\w@]*|\d+)", scrubbed_field
    )
    targets.sort(key=len, reverse=True)

    for t in targets:
        scrubbed_field = scrubbed_field.replace(t, "0" * len(t))
    scrubbed_field = re.sub(
        r"\\+", "", re.sub(r'(?!\B"[^"]*)0+(?![^"]*"\B)', "0", scrubbed_field)
    )

    data_dict[field] = jh.deserialize(scrubbed_field)
    return jh.serialize(data_dict)


def scrub_id(data: dict, regex: None | str = None) -> dict:
    """
    This removes id's from a response report object.

    Args:
        data: A response report object.
        regex: The regex to locate anything (id's) for scrubbing (defaults to uuid's).

    Returns:
        data: A scrubbed response report object.
    """
    regex = (
        regex
        or r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
    )

    data_message = {k: jh.ensure_serializable(v) for k, v in data.items()}
    data_message = jh.serialize(data_message)

    ids = list(set(re.findall(regex, str(data))))
    if ids:
        uuid_rep = re.sub(r"[^-]", "0", ids[0])
        data_message = re.sub("|".join(ids), uuid_rep, data_message)

    headers = data.get("HEADERS") or data.get("headers")
    if headers:
        header_reps = [
            [v, "0" * len(v)]
            for k, v in headers.items()
            if len(re.findall(r"\d", str(v))) > 1
        ]
        for h in header_reps:
            data_message = data_message.replace(h[0], h[1])

    if data.get("message") and "2" == data["actual_code"][0]:
        data_message = scrub_field(data_message, "message")

    if data.get("message") and "4" == data["actual_code"][0]:
        targets = re.findall(r'"(.+?)"', str(data["message"]))
        targets = [
            [t, re.findall(r"([A-Za-z]+[\d@]+[\w@]*|[\d@]+[A-Za-z]+[\w@]*|\d+)", t)]
            for t in targets
        ]

        reps = [[t[0], re.sub("|".join(t[1]), "0", t[0])] for t in targets if t[1]]
        for r in reps:
            data_message = data_message.replace(r[0], r[1])

    if data.get("body"):
        data_message = scrub_field(data_message, "body")

    return jh.deserialize(data_message)


async def csv_to_dict(csv_data: str | list, scrub: bool = False) -> list[dict]:
    """

    Args:
        csv_data: The path to the csv file to be read in or the data itself.
        scrub: Whether to remove sensitive info from the data.

    Returns:
        data: The csv file represented as a dictionary.
    """
    if isinstance(csv_data, str):
        async with aopen(csv_data, encoding="ascii", newline="") as csv_file:
            data = [row async for row in AsyncDictReader(csv_file)]
    elif isinstance(csv_data, list):
        data = [dict(zip(csv_data[0], r)) for r in csv_data[1:] if r]

    if scrub:
        data = [scrub_id(d) for d in data]

    for row in data:
        for k, v in row.items():
            if v:
                row[k] = jh.deserialize(v, safe=True)

    return data


async def create_csv_report(csv_path: str, _return: dict, scrub: bool = False):
    """
    This writes the results of each batch of requests to a csv report file.

    Args:
        csv_path: The path to store the csv report.
        _return: The _return from a batch request.
        scrub: Whether to remove sensitive info from the data.
    """
    responses = _return["responses"]

    for r in responses:
        r["server_headers"] = {k: v for k, v in r["server_headers"].items()}

        kwargs = r.get("kwargs", {})
        r["body"] = kwargs.pop("message", {}) or kwargs.pop("data", {})
        if "FormData" in str(type(r["body"])):
            r["body"] = r["body"]._fields
        elif isinstance(r["body"], dict):
            update = {
                k: v.name
                for k, v in r["body"].items()
                if "BufferedReader" in str(type(v))
            }
            r["body"].update(update)

        r["response_seconds"] = r.pop("response_seconds")
        r["delay_seconds"] = r.pop("delay_seconds")

    col_titles = [""]
    if not await aos.path.exists(csv_path):
        col_titles = [[key.upper() for key in responses[0].keys()]]

    csv_data = col_titles + [list(r.values()) for r in responses]
    await add_rows_to_csv_report(csv_path, csv_data)

    if scrub:
        scrubbed_csv_path = csv_path.replace(".csv", "_scrubbed.csv")

        scrubbed_responses = [
            {k: v if k != "curl" else "" for k, v in r.copy().items()}
            for r in responses
        ]
        scrubbed_responses = [scrub_id(r) for r in scrubbed_responses]

        col_titles = [""]
        if not await aos.path.exists(scrubbed_csv_path):
            col_titles = [[key.upper() for key in responses[0].keys()]]

        csv_data = col_titles + [list(r.values()) for r in scrubbed_responses]
        await add_rows_to_csv_report(scrubbed_csv_path, csv_data)


async def add_rows_to_csv_report(csv_path: None | str, csv_data: list[list], mode="a+"):
    """
    This adds a row(s) to an existing csv report

    Args:
        csv_path: The path to the csv file. If path is None the default one is found and used.
        csv_data: The column to add to the report.
        mode: The mode of writing to the csv file.
    """
    if not isinstance(csv_data, list):
        csv_data = [[csv_data]]

    for data in csv_data[1:]:
        for i, cell in enumerate(data):
            if isinstance(cell, (dict, list)):
                data[i] = jh.serialize(cell)

    async with aopen(csv_path, mode=mode, encoding="ascii", newline="") as csv_file:
        writer = AsyncWriter(csv_file)
        await writer.writerows(csv_data)


async def delete_last_n_rows_from_csv_report(csv_path: None | str, rows: int = 1):
    """
    This removes the last n row(s) from an existing csv report.

    Args:
        csv_path: The path to the csv file. If path is None the default one is found and used.
        rows: The last n rows to remove.
    """
    async with aopen(csv_path, encoding="ascii", newline="") as csv_file:
        content = await csv_file.read()
    reader = csv.reader(content.splitlines())
    data = [row for row in reader]

    await add_rows_to_csv_report(csv_path, data[:-rows], mode="w")


async def add_column_to_csv_report(csv_path: str, column: list):
    """
    This adds a column to an existing csv report

    Args:
        csv_path: The path to the csv file.
        column: The column to add to the report.
    """
    rows = await read_csv(csv_path)

    rows_no_newlines = np.array([r for r in rows if r])
    normalized_column = np.array(
        [column[0]] + [""] * (len(rows_no_newlines) - len(column)) + column[1:]
    )
    new_rows = np.column_stack([rows_no_newlines, normalized_column]).tolist()

    newline_indices = [i for i, row in enumerate(rows) if not row]
    for ni in newline_indices:
        new_rows.insert(ni, [])

    await add_rows_to_csv_report(csv_path, new_rows, mode="w")
