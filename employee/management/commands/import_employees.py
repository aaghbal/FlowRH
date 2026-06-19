import json
import os
import time
import traceback
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.db import transaction, OperationalError
from django.db.utils import DatabaseError
from django.db import connection
from base.models import Site
from employee.models import Employee, EmployeeWorkInformation, EmployeeBankDetails
from base.models import Company, Department, JobPosition, JobRole, EmployeeType, WorkType

# Constants for retry mechanism
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds

class Command(BaseCommand):
    help = 'Import employees from JSON file to database'

    def add_arguments(self, parser):
        parser.add_argument('json_file', type=str, help='Path to the JSON file')

    def handle(self, *args, **options):
        json_file = options['json_file']
        processed = 0
        success = 0
        errors = 0
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                employees_data = json.load(f)
                total_employees = len(employees_data)
                self.stdout.write(self.style.SUCCESS(f'Starting import of {total_employees} employees...'))
                
                for i, emp_data in enumerate(employees_data, 1):
                    processed += 1
                    # Show progress
                    if i % 10 == 0 or i == total_employees:
                        self.stdout.write(self.style.SUCCESS(f'Processing employee {i}/{total_employees}...'))
                    
                    # Retry mechanism for database operations
                    retry_count = 0
                    success = False
                    
                    while retry_count < MAX_RETRIES and not success:
                        try:
                            # Use savepoint for each employee to prevent partial imports on error
                            sid = transaction.savepoint()
                            with transaction.atomic():
                                # Create or get default company and department
                                company, _ = Company.objects.get_or_create(company='Default Company')
                                department, _ = Department.objects.get_or_create(department='Automotiv')
                            
                            # Get or create Automotiv if not exists
                            default_department, _ = Department.objects.get_or_create(
                                department='Automotiv',
                                defaults={'company': company}
                            )
                            
                            # Get or create job position with department
                            job_title = emp_data.get('Fonction', 'Automotiv')
                            if job_title:
                                job_position, _ = JobPosition.objects.get_or_create(
                                    job_position=job_title,
                                    defaults={'department_id': default_department}
                                )
                                
                                # Ensure the job position has a department
                                if not job_position.department_id:
                                    job_position.department_id = default_department
                                    job_position.save()
                            else:
                                job_position = None
                            
                            # Get or create employee
                            badge_id = str(emp_data.get('Matricule', ''))
                            try:
                                employee = Employee.objects.get(badge_id=badge_id)
                                update_employee = True
                            except Employee.DoesNotExist:
                                employee = Employee(badge_id=badge_id)
                                update_employee = False
                            
                            # Prepare employee data
                            employee.employee_first_name = emp_data.get('Prenom', '').strip()
                            employee.employee_last_name = emp_data.get('Nom', '').strip()
                            employee.email = f"{emp_data.get('Prenom', '').lower().strip()}.{emp_data.get('Nom', '').lower().strip()}@example.com"
                            employee.phone = ''
                            employee.qualification = emp_data.get('CIN', '')
                            
                            # Handle date of birth
                            try:
                                dob_str = emp_data.get('dt_naissance')
                                if dob_str:
                                    employee.dob = datetime.strptime(dob_str, '%d/%m/%Y').date()
                            except (ValueError, TypeError):
                                self.stdout.write(self.style.WARNING(f'Invalid date format for employee {employee.employee_first_name} {employee.employee_last_name}. Using default date.'))
                                employee.dob = datetime(1970, 1, 1).date()
                            
                            # Save or update Employee
                            employee.save()
                            action = 'Updated' if update_employee else 'Created'
                            self.stdout.write(self.style.SUCCESS('{} employee: {} {} (ID: {})'.format(
                                action,
                                employee.employee_first_name,
                                employee.employee_last_name,
                                employee.badge_id
                            )))
                            success = True  # Mark as successful if we get here
                            
                            # Resolve the site (free text in the source file -> Site row)
                            site_name = emp_data.get('Sites', '').strip()
                            site_obj = None
                            if site_name:
                                site_obj, _ = Site.objects.get_or_create(site_name=site_name)

                            # Prepare work info data
                            work_info_data = {
                                'employee_id': employee,
                                'company_id': company,
                                'department_id': department,
                                'job_position_id': job_position,
                                'location': site_obj,
                                'email': str(emp_data.get('NO CNSS', '')),  # Storing CNSS number in email field
                                'mobile': emp_data.get('AFFIL CIMR', '').strip(),
                                'numero_cimr': str(emp_data.get('NO CIMR', '')),
                                'societe': emp_data.get('societe', '').strip(),
                                'affiliation_cnss': emp_data.get('AFFIL CNSS', '').strip(),
                                'affiliation_mut': emp_data.get('AFFIL MUT', '').strip(),
                            }
                            
                            # Handle contract start date
                            try:
                                contract_date = emp_data.get('deb contrat')
                                if contract_date:
                                    work_info_data['date_joining'] = datetime.strptime(contract_date, '%d/%m/%Y').date()
                                else:
                                    work_info_data['date_joining'] = datetime(1990, 1, 1).date()
                            except (ValueError, TypeError):
                                work_info_data['date_joining'] = datetime(1990, 1, 1).date()
                            
                            # Create or update EmployeeWorkInformation
                            work_info, created = EmployeeWorkInformation.objects.get_or_create(
                                employee_id=employee,
                                defaults=work_info_data
                            )
                            if not created:
                                # Update existing work info
                                for key, value in work_info_data.items():
                                    setattr(work_info, key, value)
                                work_info.save()
                            
                            # Create or update EmployeeBankDetails with null/empty handling
                            bank_name = emp_data.get('BANQUE')
                            account_number = emp_data.get('NO COMPTE')
                            
                            # Only create/update bank details if we have at least one piece of bank info
                            if bank_name or account_number:
                                bank_details, created = EmployeeBankDetails.objects.get_or_create(
                                    employee_id=employee,
                                    defaults={
                                        'bank_name': bank_name.strip() if bank_name else '',
                                        'account_number': str(account_number).strip() if account_number else '',
                                    }
                                )
                                if not created:
                                    # Update existing bank details
                                    if bank_name is not None:
                                        bank_details.bank_name = bank_name.strip()
                                    if account_number is not None:
                                        bank_details.account_number = str(account_number).strip()
                                    bank_details.save()
                            
                        except (OperationalError, DatabaseError) as e:
                            transaction.savepoint_rollback(sid)
                            retry_count += 1
                            
                            if 'database is locked' in str(e).lower() and retry_count < MAX_RETRIES:
                                wait_time = RETRY_DELAY * retry_count
                                self.stdout.write(self.style.WARNING(
                                    f'Database is locked, retrying in {wait_time} seconds... (Attempt {retry_count}/{MAX_RETRIES})'
                                ))
                                time.sleep(wait_time)
                                
                                # Close any existing connections to avoid stale connections
                                connection.close()
                                continue
                            
                            errors += 1
                            self.stdout.write(self.style.ERROR(f'Error importing employee: {str(e)}'))
                            break  # Exit retry loop on max retries or other errors
                            
                        except Exception as e:
                            transaction.savepoint_rollback(sid)
                            errors += 1
                            self.stdout.write(self.style.ERROR(f'Error importing employee: {str(e)}'))
                            break  # Exit retry loop on non-database errors
                            
                            success += 1
                            # Commit after each successful employee import
                            transaction.savepoint_commit(sid)
                            break  # Exit retry loop on success
                            
                self.stdout.write(self.style.SUCCESS('\nImport completed!'))
                self.stdout.write(self.style.SUCCESS(f'Successfully processed: {success}'))
                self.stdout.write(self.style.WARNING(f'Failed to process: {errors}'))
                
                # Close the database connection
                connection.close()
                
        except FileNotFoundError as e:
            self.stdout.write(self.style.ERROR(f'File {json_file} not found.'))
            if hasattr(e, '__traceback__'):
                self.stdout.write(self.style.ERROR('Traceback:'))
                self.stdout.write(self.style.ERROR(traceback.format_exc()))
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR('Invalid JSON file.'))
            if hasattr(e, '__traceback__'):
                self.stdout.write(self.style.ERROR('Traceback:'))
                self.stdout.write(self.style.ERROR(traceback.format_exc()))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error importing employees: {str(e)}'))
            if hasattr(e, '__traceback__'):
                self.stdout.write(self.style.ERROR('Traceback:'))
                self.stdout.write(self.style.ERROR(traceback.format_exc()))
        finally:
            self.stdout.write(self.style.SUCCESS(f'\nImport summary:'))
            self.stdout.write(self.style.SUCCESS(f'Total processed: {processed}'))
            self.stdout.write(self.style.SUCCESS(f'Successfully imported: {success}'))
            self.stdout.write(self.style.ERROR(f'Failed: {errors}'))
