import json

import pytest


class Vars:
    DATA_FOLDER = "data1-D7961558"
    BUDGET_FOLDER = "37FD3C36-7C59-A459-1374-69DF8CA2E4C2"
    FULL_KNOWLEDGE = "A-6744,B-19,C-1721,D-458,E-172,F-623,G-109,H-230"


@pytest.fixture
def ynab4file(tmp_path):
    """Build a fresh dummy data folder in pytest's tmp_path directory for each test run"""
    home = tmp_path / "MyBudget~3F76EF73.ynab4"
    data = home / Vars.DATA_FOLDER
    devices = data / "devices"
    budget = data / Vars.BUDGET_FOLDER
    home.mkdir()
    data.mkdir()
    devices.mkdir()
    budget.mkdir()

    (home / "Budget.ymeta").write_text(
        '{\n\t"formatVersion": "2",\n'
        f'\t"relativeDataFolderName": "{Vars.DATA_FOLDER}",\n'
        '\t"TED": 17347566400000\n}'
    )
    # ydevice data taken from https://jack.codes/projects/2016/09/13/reversing-the-ynab-file-format-part-1/
    (devices / "A.ydevice").write_text(
        "{\n"
        '"deviceType": "Desktop (AIR), OS:Windows XP 64",\n'
        f'"knowledgeInFullBudgetFile": "{Vars.FULL_KNOWLEDGE}",\n'
        '"friendlyName": "x200",\n'
        f'"deviceGUID": "{Vars.BUDGET_FOLDER}",\n'
        '"hasFullKnowledge": true,\n'
        '"formatVersion": "2",\n'
        f'"knowledge": "{Vars.FULL_KNOWLEDGE}",\n'
        '"highestDataVersionImported": "4.2",\n'
        '"shortDeviceId": "A",\n'
        '"YNABVersion": "Desktop version: YNAB 4 v4.3.857 (com.ynab.YNAB4.LiveCaptive), AIR Version: 4.0.0.1390",\n'
        '"lastDataVersionFullyKnown": "4.2"\n}'
    )
    (devices / "B.ydevice").write_text(
        """{
  "YNABVersion": "Android build 3.2.0",
  "deviceGUID": "F562ADE7-8344-38CC-BC05-3421871F38DE",
  "deviceType": "Android",
  "formatVersion": "2",
  "friendlyName": "GT-I9505",
  "hasFullKnowledge": false,
  "highestDataVersionImported": "4.2",
  "knowledge": "A-178,B-19",
  "knowledgeInFullBudgetFile": null,
  "lastDataVersionFullyKnown": "4.2",
  "shortDeviceId": "B"
}"""
    )
    (budget / "Budget.yfull").write_text("")
    return {"home": home, "data": data, "devices": devices, "budget": budget}


@pytest.fixture
def devices(ynab4file):
    """
    Returns {'shortDeviceId': {'knowledge_letter': knowledge_number}}
    where 'shortDeviceId' = each *.ydevice file found
    """
    return {
        device.stem: json.loads(device.read_text())
        for device in ynab4file["devices"].glob("*.ydevice")
    }


@pytest.fixture
def devices_knowledge(devices):
    """
    Format: {'knowledge_letter': knowledge_number} for a single shortDeviceId
    where len(dict) = count of comma-separated knowledge codes within *.ydevice
    """
    devices_knowledge = {}
    for d in devices:
        k = devices[d]["knowledge"].split(",")
        devices_knowledge[d] = {k_str.split("-")[0]: int(k_str.split("-")[1]) for k_str in k}
    return devices_knowledge


@pytest.fixture
def highest_knowledge(devices, devices_knowledge):
    """
    Format: {shortDeviceId: knowledge_number} where 'shortDeviceId' = each *.ydevice file found
    and knowledge_number is the number after the hyphen where 'shortDeviceId' == knowledge_letter
    """
    k = {}
    for shortDeviceId in devices:
        k[shortDeviceId] = devices_knowledge[shortDeviceId][shortDeviceId]
    return k
