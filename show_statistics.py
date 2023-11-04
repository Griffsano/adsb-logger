from tabulate import tabulate

from Database import Database
from settings import config

database = Database(config, True)
table_format = "outline"

result = database.evaluate_totals()
print(result)
print(tabulate(result[1:], headers=result[0], tablefmt=table_format))

for entry in ["flight", "registration", "type", "airline"]:
    result = database.evaluate_entries(entry)
    print(result)
    print(tabulate(result[1:], headers=result[0], tablefmt=table_format))

result = database.evaluate_records()
print(result)
print(tabulate(result[1:], headers=result[0], tablefmt=table_format))
