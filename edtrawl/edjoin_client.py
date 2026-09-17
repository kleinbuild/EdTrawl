import requests
from datetime import datetime
from edtrawl.db import upsert_listings
from edtrawl.db import LISTINGS_COLUMNS

resp = requests.get(
    "https://edjoin.org/Home/LoadJobs",
    params = {
        "rows": rows,
        "page": page,
        "sort": sort,
        "sortVal": sort_value,
        "order": order,
        "keywords": keywords,
        "location": location,
        "searchType": searchType,
        "regions": regions,
        "jobTypes": jobTypes,
        "days": daysFromPosting,
        "empType": employmentType,
        "catID": categoryID,
        "onlineApps": onlineApps,
        "recruitmentCenterID": 0,
        "stateID": 0,
        "regionID": 0,
        "districtID": 0,
        "searchID": 0,
        }
)

print(resp.url)

data = response.json()

print(data)

# hardcoded test run
# resp = requests.get(
#     "https://edjoin.org/Home/LoadJobs",
#     params = {
#         "rows": 8,
#         "page": 1,
#         "sort": 'postingDate',
#         "sortVal": 1,
#         "order": 'ASC',
#         "keywords": 'substitute',
#         "location": 'Los Angeles',
#         "searchType": '',
#         "regions": '',
#         "jobTypes": '',
#         "days": 7,
#         "empType": 'full',
#         "catID": 1,
#         "onlineApps": 'true',
#         "recruitmentCenterID": 0,
#         "stateID": 0,
#         "regionID": 0,
#         "districtID": 0,
#         "searchID": 0,
#         }
# )

# print(resp.url)

# data = resp.json()

totalRecords = data['totalRecords']

displayRecords = data['displayRecords']

jobs = data['data'] 

print('The total records found was: ', totalRecords)

print('The number of records downloaded was: ',  displayRecords)

#print('Job listings retrieved: ', jobTypes)


def parse_dotnet_date(date_string):
    """Takes a date in .net JSON format eg. "/Date(175694845845)/" and converts it to a date and time"""
    ms = int(date_string.strip("/").replace("Date(", "").replace(")", ""))
    return datetime.fromtimestamp(ms / 1000)

# successful test
#print(f"This is 1820559600000 coverted to the date: {parse_dotnet_date("/Date(1820559600000)/")}")
def jobs_truncator(jobs_data):
    """Takes JSON job listings and prints only the relevant key:value pairs"""
    truncated_jobs = []
    for job in jobs:
        new_job = {
            'postingID': job['postingID'],
            'positionTitle': job['positionTitle'],
            'salaryInfo': job['salaryInfo'],
            'postingDate': parse_dotnet_date(job['postingDate']),
            'displayUntil': parse_dotnet_date(job['displayUntil']),
            'countyName': job['countyName'],
            'districtName': job['districtName'],
            'city': job['city'],
            'fullCountyName': job['fullCountyName'],
            'jobType': job['jobType'],
            'FullTimePartTime': job['FullTimePartTime']
        }
        truncated_jobs.append(new_job)
    return truncated_jobs

truncated_jobs = jobs_truncator(jobs)
print('below is truncated_jobs content:')
print(truncated_jobs)

listings_header_map = {
    'postingID': "posting_id",
    'positionTitle': "position_title",
    'salaryInfo': "salary_info",
    'postingDate': "posting_date",
    'displayUntil': "display_until",
    'countyName': "county_name",
    'districtName': "district_name",
    'city': "city",
    'fullCountyName': "full_county_name",
    'jobType': "job_type",
    'FullTimePartTime': "full_time_part_time"
}

for row in truncated_jobs:
    try:
        clean_listings_row = {listings_header_map[k]: v for k, v in row.items() if k in listings_header_map}
        listings_tuple = tuple(clean_listings_row.get(col, None) for col in LISTINGS_COLUMNS)
        upsert_listings(listings_tuple)
    except Exception as e:
        print(f"Error on row {e}")
        print(f"Row data: {row}")






