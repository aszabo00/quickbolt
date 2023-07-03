import pytest

import quickbolt.batch_generation.batch_generation as bg

pytestmark = pytest.mark.batch_generation


def test_generate_bad_bodies():
    body = {
        "str_one": "value1",
        "int_one": 2,
        "list_one": ["item1", "item2"],
        "list_two": [0, 1],
        "dict_one": {"str_two": "value2", "str_three": 3},
    }
    bad_bodies = bg.generate_bad_bodies(body)

    expected_bodies = [
        {
            "str_one": "aaaaa0",
            "int_one": 2,
            "list_one": ["item1", "item2"],
            "list_two": [0, 1],
            "dict_one": {"str_two": "value2", "str_three": 3},
        },
        {
            "str_one": "value1",
            "int_one": 0,
            "list_one": ["item1", "item2"],
            "list_two": [0, 1],
            "dict_one": {"str_two": "value2", "str_three": 3},
        },
        {
            "str_one": "value1",
            "int_one": 2,
            "list_one": ["aaaa0", "item2"],
            "list_two": [0, 1],
            "dict_one": {"str_two": "value2", "str_three": 3},
        },
        {
            "str_one": "value1",
            "int_one": 2,
            "list_one": ["item1", "aaaa0"],
            "list_two": [0, 1],
            "dict_one": {"str_two": "value2", "str_three": 3},
        },
        {
            "str_one": "value1",
            "int_one": 2,
            "list_one": ["item1", "item2"],
            "list_two": [0, 1],
            "dict_one": {"str_two": "value2", "str_three": 3},
        },
        {
            "str_one": "value1",
            "int_one": 2,
            "list_one": ["item1", "item2"],
            "list_two": [0, 0],
            "dict_one": {"str_two": "value2", "str_three": 3},
        },
        {
            "str_one": "value1",
            "int_one": 2,
            "list_one": ["item1", "item2"],
            "list_two": [0, 1],
            "dict_one": {"str_two": "aaaaa0", "str_three": 3},
        },
        {
            "str_one": "value1",
            "int_one": 2,
            "list_one": ["item1", "item2"],
            "list_two": [0, 1],
            "dict_one": {"str_two": "value2", "str_three": 0},
        },
        {
            "str_one": "aaaaa0",
            "int_one": 0,
            "list_one": ["aaaa0", "aaaa0"],
            "list_two": [0, 0],
            "dict_one": {"str_two": "aaaaa0", "str_three": 0},
        },
    ]
    assert bad_bodies == expected_bodies


def test_generate_bad_bodies_outer_list():
    body = {
        "data": [
            {
                "value": "test@example.com",
                "classifiers": ["email_address"],
                "format": "UUID",
                "storage": "VOLATILE",
            }
        ]
    }
    bad_bodies = bg.generate_bad_bodies(body)

    expected_bodies = [
        {
            "data": [
                {
                    "value": "aaaa@aaaaaaa.aaa",
                    "classifiers": ["email_address"],
                    "format": "UUID",
                    "storage": "VOLATILE",
                }
            ]
        },
        {
            "data": [
                {
                    "value": "test@example.com",
                    "classifiers": ["aaaaa_aaaaaaa"],
                    "format": "UUID",
                    "storage": "VOLATILE",
                }
            ]
        },
        {
            "data": [
                {
                    "value": "test@example.com",
                    "classifiers": ["email_address"],
                    "format": "aaaa",
                    "storage": "VOLATILE",
                }
            ]
        },
        {
            "data": [
                {
                    "value": "test@example.com",
                    "classifiers": ["email_address"],
                    "format": "UUID",
                    "storage": "aaaaaaaa",
                }
            ]
        },
        {
            "data": [
                {
                    "value": "aaaa@aaaaaaa.aaa",
                    "classifiers": ["aaaaa_aaaaaaa"],
                    "format": "aaaa",
                    "storage": "aaaaaaaa",
                }
            ]
        },
    ]
    assert bad_bodies == expected_bodies


def test_generate_bad_bodies_sub_values():
    sub_values = {"str": "b", "digit": "9"}

    body = {
        "str_one": "value1",
        "int_one": 2,
        "list_one": ["item1", "item2"],
        "list_two": [0, 1],
        "dict_one": {"str_two": "value2", "str_three": 3},
    }
    bad_bodies = bg.generate_bad_bodies(body, sub_values=sub_values)

    expected_bodies = [
        {
            "str_one": "bbbbb9",
            "int_one": 2,
            "list_one": ["item1", "item2"],
            "list_two": [0, 1],
            "dict_one": {"str_two": "value2", "str_three": 3},
        },
        {
            "str_one": "value1",
            "int_one": 9,
            "list_one": ["item1", "item2"],
            "list_two": [0, 1],
            "dict_one": {"str_two": "value2", "str_three": 3},
        },
        {
            "str_one": "value1",
            "int_one": 2,
            "list_one": ["bbbb9", "item2"],
            "list_two": [0, 1],
            "dict_one": {"str_two": "value2", "str_three": 3},
        },
        {
            "str_one": "value1",
            "int_one": 2,
            "list_one": ["item1", "bbbb9"],
            "list_two": [0, 1],
            "dict_one": {"str_two": "value2", "str_three": 3},
        },
        {
            "str_one": "value1",
            "int_one": 2,
            "list_one": ["item1", "item2"],
            "list_two": [9, 1],
            "dict_one": {"str_two": "value2", "str_three": 3},
        },
        {
            "str_one": "value1",
            "int_one": 2,
            "list_one": ["item1", "item2"],
            "list_two": [0, 9],
            "dict_one": {"str_two": "value2", "str_three": 3},
        },
        {
            "str_one": "value1",
            "int_one": 2,
            "list_one": ["item1", "item2"],
            "list_two": [0, 1],
            "dict_one": {"str_two": "bbbbb9", "str_three": 3},
        },
        {
            "str_one": "value1",
            "int_one": 2,
            "list_one": ["item1", "item2"],
            "list_two": [0, 1],
            "dict_one": {"str_two": "value2", "str_three": 9},
        },
        {
            "str_one": "bbbbb9",
            "int_one": 9,
            "list_one": ["bbbb9", "bbbb9"],
            "list_two": [9, 9],
            "dict_one": {"str_two": "bbbbb9", "str_three": 9},
        },
    ]
    assert bad_bodies == expected_bodies
