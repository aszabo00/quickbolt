import ast
import csv
import re
from copy import deepcopy

import aiofiles.os as aos
import numpy as np
from aiocsv import AsyncDictReader, AsyncReader, AsyncWriter
from aiofiles import open as aopen

import quickbolt.utils.dictionary as dh
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


def scrub(text: str) -> str:
    """
    This scrubs text of alphanumerical information.

    Args:
        text: The text to scrub.

    Returns:
        scrubbed_text: The scrubbed text.
    """
    # need to do better here
    text_dict = jh.deserialize(text)
    flat_scrubbed_text = dh.flatten(text_dict)
    for key, value in flat_scrubbed_text.items():
        if not isinstance(value, str):
            val_type = type(value).__name__
            flat_scrubbed_text[key] = f"{value} ({val_type})"
    unflat_scrubbed_text = dh.unflatten(flat_scrubbed_text)
    scrubbed_text = jh.serialize(unflat_scrubbed_text)

    targets = re.findall(
        r"([A-Za-z]+[\d@]+[\w@]*|[\d@]+[A-Za-z]+[\w@]*|\d+)", scrubbed_text
    )
    targets.sort(key=len, reverse=True)

    for t in targets:
        scrubbed_text = scrubbed_text.replace(t, "0" * len(t))

    return scrubbed_text


def scrub_data(data: dict) -> dict:
    """
    This scrubs a dict against pre-defined fields.

    Args:
        data: A response report object.

    Returns:
        scrubbed_data: A scrubbed response report object.
    """
    scrub_fields = ["message", "url", "server_headers", "headers", "kwargs", "body"]

    data_copy = deepcopy(data)
    for key, value in data_copy.items():
        if key.lower() in scrub_fields:
            data_ser = jh.serialize(value)
            data_scr = scrub(data_ser)
            data_copy[key] = jh.deserialize(data_scr)

    return data_copy


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
        data = [scrub_data(d) for d in data]

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
            r["body"] = {f[0]["name"]: f[2] for f in r["body"]._fields}
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
        scrubbed_responses = [scrub_data(r) for r in scrubbed_responses]

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
