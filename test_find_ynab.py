import json
from pathlib import Path

import pytest

import find_ynab
from conftest import Vars


# Happy path testing for existing functions
def test_get_datadir(ynab4file):
    result = find_ynab.get_datadir(ynab4file["home"])
    assert result == str(ynab4file["home"] / Vars.DATA_FOLDER)


def test_get_devices(ynab4file, devices):
    result = find_ynab.get_devices(ynab4file["data"])
    assert result == devices


def test_extract_knowledge(devices, devices_knowledge):
    for d in devices:
        result = find_ynab.extract_knowledge(devices[d])
        assert result == devices_knowledge[d]


def test_get_knowledge(devices, devices_knowledge):
    result = find_ynab.get_knowledge(devices)
    assert result == devices_knowledge


def test_get_highest_knowledge(devices_knowledge, highest_knowledge):
    result = find_ynab.get_highest_knowledge(devices_knowledge)
    assert result == highest_knowledge


def test_find_devices_with_full_knowledge(devices, highest_knowledge):
    result = find_ynab.find_devices_with_full_knowledge(devices, highest_knowledge)
    assert result == ["A"]


def test_get_budget_filename(ynab4file):
    result = find_ynab.get_budget_filename(ynab4file["home"])
    assert result == str(ynab4file["budget"] / "Budget.yfull")
