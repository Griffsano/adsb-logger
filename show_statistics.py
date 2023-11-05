from tabulate import tabulate

from Database import Database
from settings import config


# Helps to align title for table
def print_table(table: str, title: str = ""):
    print()  # Empty line
    if title:
        length = len(table.splitlines()[0])
        print(title.upper().center(length))
    print(table)


# Load database
database = Database(config, True)

# Settings for printing the statistics
table_format = "outline"
count = 5

print("Evaluating statistics for ADS-B Logger database ...")

# Table for total database entries
if False:
    result = database.evaluate_counts()
    table = tabulate(result[1:], headers=result[0], tablefmt=table_format)
    print_table(table, "Total database entries")

# Table for database entries per day, includes total values
if True:
    result = database.evaluate_days(count)
    table = tabulate(result[1:], headers=result[0], tablefmt=table_format)
    print_table(table, "Statistics per day")

# Tables for most common flights, airlines, registrations, and aircraft types
if False:
    for entry in ["flight", "airline", "registration", "type"]:
        result = database.evaluate_flights(entry, count)
        table = tabulate(result[1:], headers=result[0], tablefmt=table_format)
        print_table(table, "Most common entries")

# Tables for most common flights, airlines, registrations, and aircraft types
# To reduce the printout length, the tables are print next to each other
if True:
    entries = ["flight", "airline", "registration", "type"]
    tables = []
    for e in range(len(entries)):
        result = database.evaluate_flights(entries[e], count)
        tables.append(
            tabulate(result[1:], headers=result[0], tablefmt=table_format).splitlines()
        )
    print_table(
        tabulate(
            [list(item) for item in zip(*tables)],
            tablefmt="plain",
        ),
        "Most common entries",
    )

# Table for record values, e.g., altitude, speed, or distance
if True:
    result = database.evaluate_records()
    table = tabulate(result[1:], headers=result[0], tablefmt=table_format)
    print_table(table, "Record values")
