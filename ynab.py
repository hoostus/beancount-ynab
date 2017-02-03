import os.path
import glob
import json

def split_paths(ynab_file):
    head, budget_file = os.path.split(ynab_file)
    assert budget_file == 'Budget.yfull'

    # Split up the path into chunks
    device_root, device_uuid = os.path.split(head)
    budget_root, data = os.path.split(device_root)
    ynab_root, budget_full = os.path.split(budget_root)

    budget_full, extension = os.path.splitext(budget_full)
    budget_name, budget_uuid = budget_full.split('~')

    # There is one file per device in this subdirectory.
    devices = os.path.join(device_root, 'devices', '*')

    device_files = glob.glob(devices)

    device_map = {}
    for f in device_files:
        a_device = json.load(open(f))
        device_map[a_device['deviceGUID']] = (a_device['friendlyName'], a_device['knowledge'])

    # Check to see if knowledge is up to date?
    print(device_map[device_uuid])

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('ynab', help='Path to the YNAB file')

    args = parser.parse_args()

    split_paths(args.ynab)