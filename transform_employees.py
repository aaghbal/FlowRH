import json
from datetime import datetime

# Read the employee data
with open('all_employees.json', 'r') as f:
    employees = json.load(f)

# Transform employee data
employee_info_data = []
work_info_data = []

# Start with pk 1 since we're replacing all data
next_employee_pk = 1
next_work_pk = 1

for employee in employees:
    # Transform date format from dd/mm/yyyy to yyyy-mm-dd
    def transform_date(date_str):
        if date_str:
            try:
                return datetime.strptime(date_str, '%d/%m/%Y').strftime('%Y-%m-%d')
            except:
                return None
        return None

    # Create employee info entry
    employee_info = {
        "model": "employee.employee",
        "pk": next_employee_pk,
        "fields": {
            "badge_id": str(employee['Matricule']),
            "employee_user_id": next_employee_pk,  # Using same as pk for simplicity
            "employee_first_name": employee['Prenom'],
            "employee_last_name": employee['Nom'],
            "employee_profile": "employee/profile/default.jpg",
            "email": f"{employee['Prenom'].lower()}.{employee['Nom'].lower()}@flowrh.com",
            "phone": str(employee.get('NO CNSS', '0000000000')),  # Using CNSS as phone or default
            "address": "Not Specified",  # Required field
            "country": "Morocco",
            "state": "Not Specified",
            "city": "Casablanca",  # Most employees seem to be in Casablanca
            "zip": "20000",  # Default Casablanca zip code
            "dob": transform_date(employee['dt_naissance']),
            "gender": "Homme" if employee.get('gender') == 'M' else "Femme",  # Default to Homme
            "qualification": "Not Specified",
            "experience": "0",
            "marital_status": "single",
            "children": 0,
            "emergency_contact": str(employee.get('NO CNSS', '0000000000')),  # Using CNSS as emergency contact
            "emergency_contact_name": "Not Specified",
            "emergency_contact_relation": "Not Specified",
            "is_active": True,
            "additional_info": None,
            "is_from_onboarding": False,
            "is_directly_converted": False
        }
    }

    # Create work info entry
    work_info = {
        "model": "employee.employeeworkinformation",
        "pk": next_work_pk,
        "fields": {
            "employee_id": next_employee_pk,
            "job_position_id": 1,
            "department_id": 1,
            "work_type_id": 1,  # Setting a default value instead of None
            "employee_type_id": 1,
            "job_role_id": 1,
            "reporting_manager_id": 1,  # Setting a default manager
            "company_id": 1,
            "location": employee['Sites'],
            "email": f"{employee['Prenom'].lower()}.{employee['Nom'].lower()}@flowrh.com",
            "mobile": str(employee.get('NO CNSS', '0000000000')),  # Using CNSS as mobile
            "shift_id": 1,
            "date_joining": transform_date(employee['deb contrat']),
            "contract_end_date": None,
            "basic_salary": 0,  # Default salary
            "salary_hour": 0,
            "additional_info": None,
            "experience": 0,
            "tags": []
        }
    }

    employee_info_data.append(employee_info)
    work_info_data.append(work_info)
    next_employee_pk += 1
    next_work_pk += 1

# Replace employee_info_data.json with new data
with open('load_data/employee_info_data.json', 'w') as f:
    json.dump(employee_info_data, f, indent=2)

# Replace work_info_data.json with new data
with open('load_data/work_info_data.json', 'w') as f:
    json.dump(work_info_data, f, indent=2)

print(f"Replaced all previous employees with {len(employees)} new employees from all_employees.json") 