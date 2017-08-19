#!/usr/bin/env python

import json
import sys
import os.path
import glob

def get_datadir(root):
    meta_path = os.path.join(root, 'Budget.ymeta')
    if os.path.exists(meta_path):
        meta = json.load(open(meta_path))
        if int(meta['formatVersion']) != 2:
            print("Data not in YNAB format version 2. Instead it was %s" % meta['formatVersion'])
            sys.exit(1)
        data_dir = meta['relativeDataFolderName']
        return os.path.join(root, data_dir)
    else:
        print("No Budget.ymeta found. Are you sure it is a YNAB directory?")
        sys.exit(1)

def get_devices(data_dir):
    device_dir = os.path.join(data_dir, 'devices')
    all_devices = {}
    for device in glob.glob(os.path.join(device_dir, '*.ydevice')):
        d = json.load(open(os.path.join(device_dir, device)))
        all_devices[d['shortDeviceId']] = d
    return all_devices

def extract_knowledge(dev):
    k = {}
    k.update((a.split('-') for a in dev['knowledge'].split(',')))
    # convert everything from strings to actual ints
    for key in k:
        k[key] = int(k[key])
    return k

def get_knowledge(devices):
    all = {}
    for dev in devices.values():
        k = extract_knowledge(dev)
        all[dev['shortDeviceId']] = k
    return all

def get_highest_knowledge(knowledge):
    """ We assume that the N has the highest knowledge of N. """
    k = {}
    for key in knowledge.keys():
        k[key] = knowledge[key][key]
    return k

def find_devices_with_full_knowledge(devices, full_knowledge):
    matched = []
    for dev in devices.values():
        k = extract_knowledge(dev)
        if k == full_knowledge:
#            print('Matched', dev['friendlyName'], dev['shortDeviceId'])
            matched.append(dev['shortDeviceId'])
    return matched

def get_budget_filename(root):
    devices = get_devices(get_datadir(root))
    search = get_highest_knowledge(get_knowledge(devices))
    matched = find_devices_with_full_knowledge(devices, search)

    if not matched:
        print('No devices found with full knowledge! What?!?')
        sys.exit(1)

    for m in matched:
        guid = devices[m]['deviceGUID']
        budget = os.path.join(get_datadir(root), guid, 'Budget.yfull')
        if os.path.exists(budget):
            return budget
    print('No Budget.yfull found? Expected to find it in %s' % matched)
    sys.exit(1)

if __name__ == '__main__':
    root = sys.argv[1]
    fn = get_budget_filename(root)
    print(fn)