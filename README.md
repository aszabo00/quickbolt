# Quickbolt 

Asynchronously make and validate requests!

This was forked from [api-automation-tools](https://github.com/rakutentech/api-automation-tools).

## Installation

```console
$ pip install quickbolt
```

## Usage

### Pytest

The CorePytestBase loads **json** files from **credentials** and **data** folders during setup. Validations and reporting are performed during the teardown.

### Async requests with aiohttp or httpx

Make single or batched style async requests using aiohttp or httpx. Each request method call will generate a csv containing useful data about the request(s). The usual request arguments of aiohttp and httpx are supported.

There's a nifty function called **generate_batch** that'll intake valid (200 type) request information and return a list of corruptions for execution.

```python
from quickbolt.clients import AioRequests, HttpxRequests

aiohttp_requests = AioRequests()
httpx_requests = HttpxRequests()

batch = {'method': 'get', 'headers': {...}, 'url': '...'}
response = aiohttp_requests.request(batch)
response = httpx_requests.request(batch)

or

batch = [{'method': 'get', 'headers': {...}, 'url': '...'}, {...}, ...]
responses = aiohttp_requests.request(batch)
responses = httpx_requests.request(batch)

or 

from quickbolt.batch_generation import generate_batch

batch = generate_batch("get", ...)
responses = aiohttp_requests.request(batch)
responses = httpx_requests.request(batch)
```

Note: Both clients have an awaitable request method called async_request e.g. **await aiohttp_requests.async_request(...)** or **await httpx_requests.async_request(...)**.

Note: You can indicate where the batch generator will start looking for path parameters by placing a **semicolon (;)** where the path parameters start (before a **/**) e.g. **https://httpbin.org/get;/param/value**.

### Validations

After each **request**, a scrubbed copy of the csv history of the execution will be generated. This file (or the original) can be used to validate against executions over time. These files will have the same name as the running test, just with the **csv** extenstion instead. Any mismatches can be raised as errors and are reported in a separate csv. Historical csv files to be used as reference can be stored in a validations folder at the root level.

```python
from quickbolt.validations import Validations

...requests were made and csv files were generated...

validations = Validations()
mismatches = await validations.validate_references(actual_refs={...})
mismatches => 
[
    {
        "values": [{"key": "ACTUAL_CODE", "d1": "404", "d2": "999"}, ...],
        "keys": [...],
        "skipped_keys": [...],
        "actual_refs": {...},
        "expected_refs": {...},
        "unscrubbed_refs": {...},
    },
    {...},
]
```

### Examples

An example of a test - 
[test_get.py](examples/test_get.py)

An example of a base class showing a setup and teardown - 
[some_pytest_base.py](examples/some_pytest_base.py)

An example of the scrubbed csv report file generated from running the test - 
[get_scrubbed.csv](examples/validations/get_scrubbed.csv)

## Project structure

This package requires the following base structure for the project.
```
.
├── credentials                         # Optional - credentials
│   └── credentials.json                # Optional - credentials as json
├── tests                               # Required - test files
│   ├── data                            # Optional - test data
│   │   └── data.json                   # Optional - test data as json
│   └── test_some_request.py            # Required - pytest test
└── validations                         # Optional - validation data
    └── some_request.json               # Optional - validation data as json. the validation files 
                                                     directory structure must match the structure of the tests in the tests folder.
```