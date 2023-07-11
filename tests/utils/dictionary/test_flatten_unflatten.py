import pytest

import quickbolt.utils.dictionary as dh

pytestmark = pytest.mark.utils

test_dict_base = {
    "str1": "value1",
    "int1": 2,
    "list1": ["str1", "str2"],
    "list2": [0, 1, {"str3": 3}],
    "empty_list1": [],
    "empty_dict1": {},
    "empty_str1": "",
    "empty_tuple1": (),
}
test_dict = {**test_dict_base, **{"dict1": test_dict_base}}

expected_flat_dict = {
    "str1": "value1",
    "int1": 2,
    "list1.0": "str1",
    "list1.1": "str2",
    "list2.0": 0,
    "list2.1": 1,
    "list2.2.str3": 3,
    "empty_list1": [],
    "empty_dict1": {},
    "empty_str1": "",
    "empty_tuple1": (),
    "dict1.str1": "value1",
    "dict1.int1": 2,
    "dict1.list1.0": "str1",
    "dict1.list1.1": "str2",
    "dict1.list2.0": 0,
    "dict1.list2.1": 1,
    "dict1.list2.2.str3": 3,
    "dict1.empty_list1": [],
    "dict1.empty_dict1": {},
    "dict1.empty_str1": "",
    "dict1.empty_tuple1": (),
}


def test_flatten_dict():
    flat_dict = dh.flatten(test_dict)
    pytest.flat_dict = flat_dict
    assert expected_flat_dict == flat_dict


def test_flatten_non_dict():
    flat_dict = dh.flatten("non_dict")
    pytest.flat_non_dict = flat_dict
    assert {"": "non_dict"} == flat_dict


def test_flatten_empty_dict():
    flat_dict = dh.flatten({})
    pytest.flat_empty_dict = flat_dict
    assert {"": {}} == flat_dict


def test_flatten_list_dict():
    flat_dict = dh.flatten([test_dict, [test_dict] * 2])
    pytest.flat_list_dict = flat_dict

    expected_flat_dict = {
        "0.str1": "value1",
        "0.int1": 2,
        "0.list1.0": "str1",
        "0.list1.1": "str2",
        "0.list2.0": 0,
        "0.list2.1": 1,
        "0.list2.2.str3": 3,
        "0.empty_list1": [],
        "0.empty_dict1": {},
        "0.empty_str1": "",
        "0.empty_tuple1": (),
        "0.dict1.str1": "value1",
        "0.dict1.int1": 2,
        "0.dict1.list1.0": "str1",
        "0.dict1.list1.1": "str2",
        "0.dict1.list2.0": 0,
        "0.dict1.list2.1": 1,
        "0.dict1.list2.2.str3": 3,
        "0.dict1.empty_list1": [],
        "0.dict1.empty_dict1": {},
        "0.dict1.empty_str1": "",
        "0.dict1.empty_tuple1": (),
        "1.0.str1": "value1",
        "1.0.int1": 2,
        "1.0.list1.0": "str1",
        "1.0.list1.1": "str2",
        "1.0.list2.0": 0,
        "1.0.list2.1": 1,
        "1.0.list2.2.str3": 3,
        "1.0.empty_list1": [],
        "1.0.empty_dict1": {},
        "1.0.empty_str1": "",
        "1.0.empty_tuple1": (),
        "1.0.dict1.str1": "value1",
        "1.0.dict1.int1": 2,
        "1.0.dict1.list1.0": "str1",
        "1.0.dict1.list1.1": "str2",
        "1.0.dict1.list2.0": 0,
        "1.0.dict1.list2.1": 1,
        "1.0.dict1.list2.2.str3": 3,
        "1.0.dict1.empty_list1": [],
        "1.0.dict1.empty_dict1": {},
        "1.0.dict1.empty_str1": "",
        "1.0.dict1.empty_tuple1": (),
        "1.1.str1": "value1",
        "1.1.int1": 2,
        "1.1.list1.0": "str1",
        "1.1.list1.1": "str2",
        "1.1.list2.0": 0,
        "1.1.list2.1": 1,
        "1.1.list2.2.str3": 3,
        "1.1.empty_list1": [],
        "1.1.empty_dict1": {},
        "1.1.empty_str1": "",
        "1.1.empty_tuple1": (),
        "1.1.dict1.str1": "value1",
        "1.1.dict1.int1": 2,
        "1.1.dict1.list1.0": "str1",
        "1.1.dict1.list1.1": "str2",
        "1.1.dict1.list2.0": 0,
        "1.1.dict1.list2.1": 1,
        "1.1.dict1.list2.2.str3": 3,
        "1.1.dict1.empty_list1": [],
        "1.1.dict1.empty_dict1": {},
        "1.1.dict1.empty_str1": "",
        "1.1.dict1.empty_tuple1": (),
    }

    assert flat_dict == expected_flat_dict


def test_unflatten_dict():
    unflat_dict = dh.unflatten(pytest.flat_dict)
    assert test_dict == unflat_dict


def test_unflatten_non_dict():
    original = [test_dict, [test_dict] * 2]
    unflat_dict = dh.unflatten(pytest.flat_list_dict)
    assert unflat_dict == original


def test_unflatten_empty_dict():
    original = {}
    unflat_dict = dh.unflatten(pytest.flat_empty_dict)
    assert unflat_dict == original


def test_unflatten_list_dict():
    original = {}
    unflat_dict = dh.unflatten(pytest.flat_empty_dict)
    assert unflat_dict == original
