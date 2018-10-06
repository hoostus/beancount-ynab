# beancount-ynab

beancount is a plaintext accounting/personal finance system: https://bitbucket.org/blais/beancount/overview

This is an importer between YNAB4 -- https://www.youneedabudget.com.
YNAB4 is the previous, desktop based version, of the software.

This is designed to be run on a recurring basis: you enter data in YNAB and then
sync it into beancount. However, it also will work perfectly fine is you just
want to do a one-time migration from YNAB to beancount.

# Running the importer

Running the import is straightforward, you just point it at your YNAB file and
your beancount file.

./import.py ynab bean

It will output the beancount statements to stdout and a summary to stderr

~~~~
2016-12-31 * "Uber"
    ynab-id: "60C90246-EEF9-FB6F-8FC6-57663DF068C1"
    Assets:VN:Citibank-Visa    -25,000 VND
    Expenses:Everyday:Spending-Money

2016-12-31 * "Uber"
    ynab-id: "F266AE25-BDFA-3C59-3A79-57665331CF0A"
    Assets:VN:Citibank-Visa    -36,000 VND
    Expenses:Everyday:Spending-Money

0 errors during import
30 warnings during import.
	Check and fix income statements.
	Search for Category/__ImmediateIncome__ and Category/__DeferredIncome__.
1165 imported.
0 already imported; skipped.
Don't forget to run bean-check on the result!
~~~~

This allows you to redirect the output, appending it to your beancount file.

~~~~
./import.py ynab-file bean-file >> bean-file
0 errors during import
30 warnings during import.
	Check and fix income statements.
	Search for Category/__ImmediateIncome__ and Category/__DeferredIncome__.
1165 imported.
0 already imported; skipped.
Don't forget to run bean-check on the result!
~~~~

# Where is my YNAB file?

Buried somewhere deep inside your YNAB folder there is a file named
*Budget.yfull* which contains all of your transactions. That's the file the
importer relies on. On my machine the full path is:

`./YNAB/My Budget Test~CAB5B90E.ynab4/data1~E6B943B1/9133AEC3-2369-8AFB-52EB-CC52E6BE8478/Budget.yfull`

but it will be slightly different for you.

# Adding metadata to the beancount file

In order for the importer to map between YNAB and beancount, it relies on
metadata in the beancount file. The *ynab-name* metadata on an account tells
the importer how to match up accounts. YNAB has a two-level hierarchy of
accounts. Use a colon (:) to separate the two levels.

~~~~
2016-01-01 open Expenses:Vacation
    ynab-name: "Savings Goals:Vacation"
~~~~

## Income is a special case

All income from YNAB will come from one of two accounts:
`Categories/__DeferredIncome__` and `Categories/__ImmediateIncome__`.
You can either map those to an account

~~~~
2016-01-01 open Income:Salary
    ynab-name: "Categories/__DeferredIncome__"
~~~~

Or you can leave them unmapped. If you leave them unmapped then the importer will
generate statements that look like

~~~~
2016-01-01 * "My Company"
    Assets:VN:Cash    1,000,000 VND
    Category/__DeferredIncome__
~~~~

This is not valid syntax in beancount, so bean-check will complain. But it makes
it easy to search through your beanfile and add the correct accounts.

## Hidden Categories

YNAB has the concept of hidden categories. These are budget categories that you
are no longer using. Creating the mapping for them is a little tricky since YNAB
effectively renames them.

Imagine you had a master category called _Monthly Spending_. And inside of that
you had a subcategory called _Yoga Classes_. You've quit yoga, so you've made it
a hidden category, so that it doesn't clutter up YNAB. Normally you'd use a
mapping key of *Monthly Spending:Yoga Classes*. But since it is now a hidden
category you have to use
~~~
Hidden Categories:Monthly Spending ` Yoga ` A4
~~~
There are three things to note:

1. The master category is now _Hidden Categories_
2. YNAB uses the backtick (`) as a separator between the *old* master category
and the subcategory.
3. There's a magic number. This is an internal category id that YNAB uses.
There's really no way to know what this is other than to run the import once and
see if there are any errors about hidden categories.

# Currency

The importer will infer the currency of the transaction from the account in
beancount.

~~~~
2016-01-01 open Assets:US:Cash  USD
~~~~

YNAB only supports a single currency so this seems like a better approach
than specifying the currency in some other way. It does, however, require you
to specify the currency on the account in beancount.

# Rerunning the import

The importer will generate a *ynab-id* metadata statement for each transaction.
This allows you to re-run the importer multiple times and only import *new*
transactions. This is what makes it possible to use YNAB every day for data
entry and then sync new data over to beancount whenever you like.

~~~~
2016-12-31 * "Uber"
    ynab-id: "F266AE25-BDFA-3C59-3A79-57665331CF0A"
    Assets:VN:Citibank-Visa    -36,000 VND
    Expenses:Everyday:Spending-Money
~~~~

# What about recurring transactions?

Those aren't imported into beancount. Not yet, at least.

# What about flags/reconciliation?

YNAB has flags, that track whether a given transaction has been
reconciled or not. Those are currently not imported.
