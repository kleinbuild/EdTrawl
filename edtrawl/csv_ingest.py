#csv_ingest.py reads the CSV file and creates object that maps the info in each row to a dict. fieldnames not giving parameter allows it to take those keys from the top row values of the csv files. This is what we want. 

import csv
from csv import DictReader
from edtrawl.db import upsert_schools
from edtrawl.db import upsert_schools_snapshots
from edtrawl.db import upsert_districts
from edtrawl.db import upsert_districts_snapshots
from edtrawl.db import SCHOOL_SNAPSHOT_COLUMNS
from edtrawl.db import DISTRICTS_COLUMNS
from edtrawl.db import DISTRICTS_SNAPSHOTS_COLUMNS

schools_header_map = {
    "Academic Year": "academic_year",
    "CDS Code": "cds_code", 
    "Fed ID": "fed_id",
    "District Code": "district_code",
    "School Code": "school_code",
    "Region": "region",
    "County Name": "county_name",
    "District Name": "district_name",
    "School Name": "school_name",
    "School Type": "school_type",
    "Open Date": "open_date",
    "School Level": "school_level",
    "Grade Low": "grade_low",
    "Grade High": "grade_high",
    "Charter": "charter",
    "Charter Num": "charter_num",
    "Street": "street",
    "City": "city",
    "Zip": "zip",
    "State": "state",
    "Locale": "locale",
    "School Website": "school_website",
    "Latitude": "latitude",
    "Longitude": "longitude"
}

schools_snapshots_header_map = {
    "Academic Year": "academic_year",        
    "CDS Code": "cds_code",             
    "Charter Funding Type": "charter_fund_type",    
    "Virtual": "virtual",              
    "Magnet": "magnet",               
    "Title I": "title_i",              
    "DASS": "dass",                 
    "Assistance Status ESSA": "essa",                 
    "Enroll Total": "enroll_total",            
    "African American": "african_amer",            
    "African American (%)": "african_amer_pct",     
    "American Indian": "amer_indian",             
    "American Indian (%)": "amer_indian_pct",      
    "Asian": "asian",                   
    "Asian (%)": "asian_pct",            
    "Filipino": "filipino",                
    "Filipino (%)": "filipino_pct",                     
    "Hispanic": "hispanic",                
    "Hispanic (%)": "hispanic_pct",         
    "Pacific Islander": "pac_islander",            
    "Pacific Islander (%)": "pac_islander_pct",     
    "White": "white",                   
    "White (%)": "white_pct",            
    "Two or More Races": "two_or_more_races",       
    "Two or More Races (%)": "two_or_more_races_pct",
    "Not Reported": "not_reported",         
    "Not Reported (%)": "not_reported_pct",     
    "English Learner": "english_learner",         
    "English Learner (%)": "english_learner_pct",  
    "Foster": "foster",                  
    "Foster (%)": "foster_pct",           
    "Homeless": "homeless",                
    "Homeless (%)": "homeless_pct",          
    "Migrant": "migrant",                 
    "Migrant (%)": "migrant_pct",          
    "Socioeconomically Disadvantaged": "soc_disadvantaged",       
    "Socioeconomically Disadvantaged (%)": "soc_disadvantaged_pct",
    "Students with Disabilities": "students_with_dis",       
    "Students with Disabilities (%)": "students_with_dis_pct",
    "Free/Reduced Meal Eligible": "free_reduced_meal",       
    "Free/Reduced Meal Eligible (%)": "free_reduced_meal_pct",
    "Grade TK": "grade_tk",                
    "Grade KG": "grade_kg",                
    "Grade 1": "grade_01",                
    "Grade 2": "grade_02",                
    "Grade 3": "grade_03",                
    "Grade 4": "grade_04",                
    "Grade 5": "grade_05",                
    "Grade 6": "grade_06",                           
    "Grade 7": "grade_07",                
    "Grade 8": "grade_08",                
    "Grade 9": "grade_09",                
    "Grade 10": "grade_10",                
    "Grade 11": "grade_11",                
    "Grade 12": "grade_12",                
    "Staff Total": "staff_total",             
    "Staff Teacher": "staff_teachers",          
    "Staff Admin": "staff_admin",             
    "Staff Pupil Services": "staff_pupil_svcs",        
    "Staff Other": "staff_other"
}

districts_header_map = {
    "District Code": "district_code",
    "CDS Code": "cds_code",
    "County Name": "county_name",
    "District Name": "district_name",
    "Academic Year": "academic_year",
    "District Type": "district_type",
    "Grade Low": "grade_low",
    "Grade High": "grade_high",
    "Street": "street",
    "City": "city",
    "Zip": "zip",
    "Latitude": "latitude",
    "Longitude": "longitude",
}

districts_snapshots_header_map = {
    "Academic Year": "academic_year",                
    "Fed ID": "fed_id",                
    "CDS Code": "cds_code",
    "Assistance Status": "assistance_status",
    "Region": "region",
    "Locale Code": "locale_code",
    "Enroll Total": "enrollment_total_district",
    "Enroll Charter": "enrollment_charter",
    "Enroll Non Charter": "enrollment_non_charter",
    "African American": "african_amer",            
    "African American (%)": "african_amer_pct",     
    "American Indian": "amer_indian",             
    "American Indian (%)": "amer_indian_pct",      
    "Asian": "asian",                   
    "Asian (%)": "asian_pct",            
    "Filipino": "filipino",                
    "Filipino (%)": "filipino_pct",                     
    "Hispanic": "hispanic",                
    "Hispanic (%)": "hispanic_pct",         
    "Pacific Islander": "pac_islander",            
    "Pacific Islander (%)": "pac_islander_pct",     
    "White": "white",                   
    "White (%)": "white_pct",            
    "Two or More Races": "two_or_more_races",       
    "Two or More Races (%)": "two_or_more_races_pct",
    "Not Reported": "not_reported",         
    "Not Reported (%)": "not_reported_pct",     
    "English Learner": "english_learner",         
    "English Learner (%)": "english_learner_pct",  
    "Foster": "foster",                  
    "Foster (%)": "foster_pct",           
    "Homeless": "homeless",                
    "Homeless (%)": "homeless_pct",          
    "Migrant": "migrant",                 
    "Migrant (%)": "migrant_pct",          
    "Socioeconomically Disadvantaged": "soc_disadvantaged",       
    "Socioeconomically Disadvantaged (%)": "soc_disadvantaged_pct",
    "Students with Disabilities": "students_with_dis",       
    "Students with Disabilities (%)": "students_with_dis_pct",
    "Locale Description": "locale_description"
}

with open('25_26.csv', newline='', encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        try:
            clean_schools_row = {schools_header_map[k]: v for k, v in row.items() if k in schools_header_map}
            upsert_schools(**clean_schools_row)
        except Exception as e:
            print(f"Error on row {e}")
            print(f"Row data: {row}")

        try:
            clean_snapshots_row = {schools_snapshots_header_map[k]: v for k, v in row.items() if k in schools_snapshots_header_map}
            snapshot_tuple = tuple(clean_snapshots_row.get(col, None) for col in SCHOOL_SNAPSHOT_COLUMNS)
            upsert_schools_snapshots(snapshot_tuple)
        except Exception as e:
            print(f"Error on row {e}")
            print(f"Row data: {row}")

with open('DistrictSites2526_-2532054265423306741.csv', newline='', encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        try:
            clean_districts_row = {districts_header_map[k]: v for k, v in row.items() if k in districts_header_map}
            districts_tuple = tuple(clean_districts_row.get(col, None) for col in DISTRICTS_COLUMNS)
            upsert_districts(districts_tuple)
        except Exception as e:
            print(f"Error on row {e}")
            print(f"Row data: {row}")

        try:
            clean_districts_snapshots_row = {districts_snapshots_header_map[k]: v for k, v in row.items() if k in districts_snapshots_header_map}
            districts_snapshots_tuple = tuple(clean_districts_snapshots_row.get(col, None) for col in DISTRICTS_SNAPSHOTS_COLUMNS)
            upsert_districts_snapshots(districts_snapshots_tuple)
        except Exception as e:
            print(f"Error on row {e}")
            print(f"Row data: {row}")