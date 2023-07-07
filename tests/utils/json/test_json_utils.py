import pytest

import quickbolt.utils.json as jh

pytestmark = pytest.mark.utils

test_dict = {
    "str1": "value1",
    "int1": 2,
    "list1": ["str1", "str2"],
    "list2": [0, 1],
}
bad_test_dict = {"str1": str}


def test_ensure_serializable():
    data = jh.ensure_serializable(test_dict)
    assert data == test_dict


def test_ensure_not_serializable():
    data = jh.ensure_serializable(bad_test_dict)
    assert data == str(bad_test_dict)


def test_serialize():
    data = jh.serialize(test_dict)
    assert jh.deserialize(data) == test_dict


def test_serialize_not_safe():
    try:
        jh.serialize(bad_test_dict, safe=False)
        assert False
    except:
        pass


def test_serialize_safe():
    data = jh.serialize(bad_test_dict, safe=True)
    assert data == bad_test_dict


def test_deserialize():
    test_dict_json = jh.serialize(test_dict)
    data = jh.deserialize(test_dict_json)
    assert data == test_dict


def test_deserialize_leading_zeros():
    zeros_dict = {
        **test_dict,
        **{"leading_zeros": 0, "fake_leading_zeros": "0", "trick_zeros": 10},
    }
    zeros_dict_json = jh.serialize(zeros_dict)
    zeros_dict_json = zeros_dict_json.replace("0", "000")

    data = jh.deserialize(zeros_dict_json)
    expected_data = {
        "str1": "value1",
        "int1": 2,
        "list1": ["str1", "str2"],
        "list2": [0, 1],
        "leading_zeros": 0,
        "fake_leading_zeros": "000",
        "trick_zeros": 1000,
    }
    assert data == expected_data


def test_not_deserialize_not_safe():
    try:
        jh.deserialize(bad_test_dict, safe=False)
        assert False
    except:
        pass


def test_not_deserialize_safe():
    data = jh.deserialize(bad_test_dict, safe=True)
    assert data == bad_test_dict
