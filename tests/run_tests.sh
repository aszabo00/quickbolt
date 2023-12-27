#!/bin/bash


MARKERS="utils or logging or core_pytest_base or client or reporting or validations or batch_generation"

poetry run pytest -n 5 --dist=loadfile --cov quickbolt/ --cov-report term-missing tests/ -m "${MARKERS}" | tee pytest_run_output.txt