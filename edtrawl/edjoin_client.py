import requests

# resp = requests.get(
#     "https://edjoin.org/Home/LoadJobs",
#     params = {
#         "rows": rows,
#         "page": page,
#         "sort": sort,
#         "sortVal": sort_value,
#         "order": order,
#         "keywords": keywords,
#         "location": location,
#         "searchType": searchType,
#         "regions": regions,
#         "jobTypes": jobTypes,
#         "days": daysFromPosting,
#         "empType": employmentType,
#         "catID": categoryID,
#         "onlineApps": onlineApps,
#         "recruitmentCenterID": 0,
#         "stateID": 0,
#         "regionID": 0,
#         "districtID": 0,
#         "searchID": 0,
#         }
# )

# print(resp.url)

# data = response.json()

# print(data)

# hardcoded test run
resp = requests.get(
    "https://edjoin.org/Home/LoadJobs",
    params = {
        "rows": 8,
        "page": 1,
        "sort": 'postingDate',
        "sortVal": 1,
        "order": 'ASC',
        "keywords": 'substitute',
        "location": 'Los Angeles',
        "searchType": '',
        "regions": '',
        "jobTypes": '',
        "days": 7,
        "empType": 'full',
        "catID": 1,
        "onlineApps": 'true',
        "recruitmentCenterID": 0,
        "stateID": 0,
        "regionID": 0,
        "districtID": 0,
        "searchID": 0,
        }
)

print(resp.url)

data = resp.json()

totalRecords = data['totalRecords']

displayRecords = data['displayRecords']

# TODO fix method to retrieve specific data

jobListingsRetrieved = data['data'] ['postingID', 'positionTitle', 'salaryInfo', 'postingDate', 'displayUntil', 'countyName', 'districtName', 'city', 'fullCountyName', 'jobType', 'FullTimePartTime']

print('The total records found was: ', totalRecords)

print('The number of records downloaded was: ',  displayRecords)

print('Job listings retrieved: ', jobListingsRetrieved)
