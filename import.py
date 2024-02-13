#!/usr/bin/env python

import json
import sys
import pprint
import collections
import datetime

import beancount.loader
import beancount.core

import find_ynab

TRANSACTION_TEMPLATE = """%(date)s * "%(payee)s"
    ynab-id: "%(ynabid)s"
    %(from_account)s    %(amount)s %(commodity)s
    %(to_account)s
"""

TRANSACTION_TEMPLATE_WITH_MEMO = """%(date)s * "%(payee)s" "%(memo)s"
    ynab-id: "%(ynabid)s"
    %(from_account)s    %(amount)s %(commodity)s
    %(to_account)s
"""

INCOME_ACCOUNTS = ('Category/__ImmediateIncome__', 'Category/__DeferredIncome__')

YNAB = collections.namedtuple('YNAB', ['transactions', 'categories', 'accounts', 'payees'])

def build_account_mapping(beancount_fname):
    account_mapping = {}
    commodity = None

    entries, errors, options = beancount.loader.load_file(beancount_fname)
    for entry in entries:
        if isinstance(entry, beancount.core.data.Open):
            if 'ynab-name' in entry.meta:
                # Use whatever currency is defined for this account.
                if entry.currencies:
                    if not commodity:
                        assert len(entry.currencies) == 1, 'YNAB only supports a single currency on accounts'
                        commodity = entry.currencies[0]
                    if commodity and commodity != entry.currencies[0]:
                        print(commodity, entry, entry.currencies[0])
                        raise("Commodity is being redefined but YNAB only supports one currency.")
                account_mapping[entry.meta['ynab-name']] = entry.account

    return entries, account_mapping, commodity

def load_ynab(filename):
    ynab = json.load(open(filename, encoding='utf-8-sig'))
    payees = entity_dict(ynab['payees'])
    accounts = entity_dict(ynab['accounts'])
    categories = get_categories(ynab['masterCategories'])
    return YNAB(transactions=ynab['transactions'], payees=payees, accounts=accounts, categories=categories)

def entity_dict(data):
    """ YNAB structures things as array rather than dicts. Convert to a
    dict to make looking things up by entityId easier """
    r = {}
    for d in data:
        r[d['entityId']] = d
    return r

def get_categories(data):
    all = entity_dict(data)
    for m in data:
        if 'isTombstone' in m: continue
        if not m['subCategories']: continue
        new_dict = entity_dict(m['subCategories'])
        all.update(new_dict)
    return all

def get_beancount_account(entity_id, accounts, account_mapping):
    ynab_name = accounts[entity_id]['accountName']
    return account_mapping[ynab_name]

def get_beancount_category(entity_id, categories, account_mapping):
    # Income is special in YNAB...it doesn't really track where it comes from very
    # well.
    if entity_id in INCOME_ACCOUNTS:
        return account_mapping.get(entity_id, entity_id)

    subcategory = categories[entity_id]
    master = categories[subcategory['masterCategoryId']]
    ynab_category =  '%s:%s' % (master['name'], subcategory['name'])
    return account_mapping[ynab_category]

def convert_ynab(txn, ynab, account_mapping, commodity):
    vars = {}
    vars['date'] = txn['date']
    vars['payee'] = ynab.payees[txn['payeeId']]['name']
    vars['memo'] = txn.get('memo')
    vars['from_account'] = get_beancount_account(txn['accountId'], ynab.accounts, account_mapping)
    vars['ynabid'] = txn['entityId']
    
    # We always insert commas.
    vars['amount'] = "{:,}".format(txn['amount'])

    vars['commodity'] = commodity

    # We don't want to emit double transactions for transfers...
    # YNAB handles this by putting the other leg's entityId in the transactionId
    # We can use that to deduplicate
    if txn.get('transferTransactionId'):
        vars['to_account'] = get_beancount_account(txn['targetAccountId'], ynab.accounts, account_mapping)
    else:
        vars['to_account'] = get_beancount_category(txn['categoryId'], ynab.categories, account_mapping)

    return vars

def import_transactions(ynab, account_mapping, commodity, previous_imports, since=None):
    # This is used to de-duplicate transfers. YNAB creates two transactions
    # (one for each account) but we only create one (which has 2 legs)
    transfers = []

    errors = []
    warnings = []
    skipped = 0
    unreconciled = 0
    imported = 0

    for txn in ynab.transactions:
        txn_date = datetime.datetime.strptime(txn['date'], "%Y-%m-%d")
        if since and txn_date < since: continue
        # From https://jack.codes/projects/2016/09/13/reversing-the-ynab-file-format-part-1/
        # "Deleted transactions are not deleted but have their “isTombstone” flag set to true."
        if 'isTombstone' in txn: continue
        # TODO: why are $0 transactions in YNAB?
        if txn['amount'] == 0: continue
        # Skip transactions that haven't been reconciled
        if txn['cleared'] != 'Reconciled':
            unreconciled += 1
            continue
        # We've already imported it once before into beancount
        if txn['entityId'] in previous_imports:
            skipped += 1
            continue

        transfer_id = txn.get('transferTransactionId')
        # Skip if we already handled this via the other account
        if (txn['entityId'] in transfers) or (transfer_id in previous_imports):
            assert transfer_id # We should only do this if it has a transfer id
            skipped += 1
            continue

        if transfer_id:
            transfers.append(transfer_id)

        try:
            vars = convert_ynab(txn, ynab, account_mapping, commodity)
            if vars['memo']:
                # Double quotes are special beancount so we need to replace any in the source data
                vars['memo'] = vars['memo'].replace('"', "'")
                t = TRANSACTION_TEMPLATE_WITH_MEMO % vars
            else:
                t = TRANSACTION_TEMPLATE % vars
            print(t)

            imported += 1

            if vars['from_account'] in INCOME_ACCOUNTS or vars['to_account'] in INCOME_ACCOUNTS:
                warnings.append(txn)

        except Exception as e:
            print('>>> Error extracting YNAB information for', txn)
            errors.append((e, txn))
            raise(e)

    return errors, warnings, skipped, imported, unreconciled

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description="Convert a YNAB file to beancount statements"
    )
    parser.add_argument('ynab', help='Path to the YNAB root directory.')
    parser.add_argument('bean', help='Path to the beancount file.')
    parser.add_argument('--since', help='Format: YYYY-MM-DD; 2016-12-30. Only process transactions after this date. This will include transactions that occurred exactly on this date.')
    args = parser.parse_args()
    if args.since:
        args.since = datetime.datetime.strptime(args.since, "%Y-%m-%d")

    ynab = load_ynab(find_ynab.get_budget_filename(args.ynab))
    entries, account_mapping, commodity = build_account_mapping(args.bean)

    previous_imports = []
    for e in entries:
        if not isinstance(e, beancount.core.data.Transaction): continue
        if 'ynab-id' in e.meta:
            previous_imports.append(e.meta['ynab-id'])

    errors, warnings, skipped, imported, unreconciled = import_transactions(ynab, account_mapping, commodity, previous_imports, since=args.since)

    print(len(errors), "errors during import", file=sys.stderr)
    if errors:
        pprint.pprint(errors, stream=sys.stderr)
    print(len(warnings), "warnings during import.", file=sys.stderr)
    if warnings:
        print("\tCheck and fix income statements.", file=sys.stderr)
        print("\tSearch for Category/__ImmediateIncome__ and Category/__DeferredIncome__.", file=sys.stderr)
    print(imported, "imported.", file=sys.stderr)
    print(unreconciled, "unreconciled. <<Only reconciled transactions are imported>>", file=sys.stderr)
    print(skipped, "already imported; skipped.", file=sys.stderr)
    print("Don't forget to run bean-check on the result!", file=sys.stderr)
