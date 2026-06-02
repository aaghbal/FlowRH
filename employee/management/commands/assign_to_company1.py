import time
from django.core.management.base import BaseCommand
from django.db import transaction, connection
from django.db.utils import OperationalError
from employee.models import Employee, EmployeeWorkInformation
from base.models import Company

class Command(BaseCommand):
    help = 'Assign all employees to company with ID 1 and ensure work information exists'

    def handle(self, *args, **options):
        try:
            # Get company with ID 1
            company = Company.objects.get(id=1)
            self.stdout.write(self.style.SUCCESS(f'Found company: {company.company} (ID: {company.id})'))
            
            # Get all employees
            employees = Employee.objects.all()
            total_employees = employees.count()
            
            if total_employees == 0:
                self.stdout.write(self.style.WARNING('No employees found in the database.'))
                return
                
            self.stdout.write(self.style.SUCCESS(f'Found {total_employees} employees to update'))
            
            updated_count = 0
            created_count = 0
            failed_count = 0
            
            # Process in smaller batches to avoid timeouts
            batch_size = 50
            total_batches = (total_employees + batch_size - 1) // batch_size
            
            for batch_num in range(total_batches):
                batch_start = batch_num * batch_size
                batch_end = batch_start + batch_size
                batch = employees[batch_start:batch_end]
                
                self.stdout.write(f'Processing batch {batch_num + 1}/{total_batches} (employees {batch_start + 1} to {min(batch_end, total_employees)})')
                
                for employee in batch:
                    max_retries = 3
                    retry_delay = 1  # seconds
                    
                    for attempt in range(max_retries):
                        try:
                            with transaction.atomic():
                                # Get or create work information for the employee
                                work_info, created = EmployeeWorkInformation.objects.get_or_create(
                                    employee_id=employee,
                                    defaults={
                                        'company_id': company,
                                        'is_active': True
                                    }
                                )
                                
                                # Update company if it's different
                                if work_info.company_id != company:
                                    work_info.company_id = company
                                    work_info.save()
                                    updated_count += 1
                                elif created:
                                    created_count += 1
                                
                                # Success - break out of retry loop
                                break
                                
                        except OperationalError as e:
                            if 'database is locked' in str(e) and attempt < max_retries - 1:
                                # Wait before retrying
                                time.sleep(retry_delay * (attempt + 1))
                                # Close the connection to avoid stale connections
                                connection.close()
                                self.stdout.write(self.style.WARNING(
                                    f'Database locked, retrying ({attempt + 1}/{max_retries})...'
                                ))
                                continue
                            else:
                                self.stdout.write(self.style.ERROR(
                                    f'Failed to update employee {employee.id}: {str(e)}'
                                ))
                                failed_count += 1
                                break
            
            self.stdout.write(self.style.SUCCESS('\nUpdate complete!'))
            self.stdout.write(self.style.SUCCESS(f'Successfully processed: {updated_count + created_count} employees'))
            self.stdout.write(self.style.SUCCESS(f'  - Updated work information: {updated_count}'))
            self.stdout.write(self.style.SUCCESS(f'  - Created work information: {created_count}'))
            if failed_count > 0:
                self.stdout.write(self.style.WARNING(f'  - Failed to process: {failed_count}'))
            
        except Company.DoesNotExist:
            self.stdout.write(self.style.ERROR('Company with ID 1 does not exist. Please create it first.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'An error occurred: {str(e)}'))
