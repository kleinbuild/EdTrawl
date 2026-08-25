#csv_ingest.py reads the CSV file and creates object that maps the info in each row to a dict. fieldnames not giving parameter allows it to take those keys from the top row values of the csv files. This is what we want. 

import csv
from csv import DictReader


with open('placeholder_name.csv', newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f, fieldnames=None, restkey=None, restval=None, dialect='excel')
    for row in reader:
        print(row)

