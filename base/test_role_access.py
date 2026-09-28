"""
End-to-end check of the role deny layer, reproducing the screenshot's role:
"test role" granting only employee.policies (Règles internes).
"""

from django.contrib.auth.models import User
from django.test import TestCase

from base.models import Company, Department, JobPosition, Role
from base.role_pages import DEFAULT_PAGES
from employee.models import Employee, EmployeeWorkInformation


class RoleDenyTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(company="M-automotiv", id=1)
        department = Department.objects.create(department="Automotiv")
        cls.position = JobPosition.objects.create(
            job_position="Mecanicien", department_id=department
        )
        cls.user = User.objects.create_user("holder", "h@x.com", "pw")
        cls.user.is_new_employee = False
        cls.user.save()
        cls.employee = Employee.objects.create(
            employee_first_name="Abdelali",
            employee_last_name="Hakimi",
            email="holder@example.com",
            employee_user_id=cls.user,
        )
        cls.work_info(cls.employee)
        cls.free = User.objects.create_user("free", "f@x.com", "pw")
        cls.free.is_new_employee = False
        cls.free.save()
        cls.work_info(
            Employee.objects.create(
                employee_first_name="No",
                employee_last_name="Role",
                email="free@example.com",
                employee_user_id=cls.free,
            )
        )

    @classmethod
    def work_info(cls, employee):
        # a role's holders are resolved through the company-scoped manager, so
        # an employee with no work information is not picked up by Role.sync()
        EmployeeWorkInformation.objects.update_or_create(
            employee_id=employee,
            defaults={"company_id": cls.company, "job_position_id": cls.position},
        )

    def setUp(self):
        from base import role_access

        role_access.invalidate()
        self.role = Role.objects.create(name="test role", pages={"employee.policies": "view"})
        self.role.employees.add(self.employee)

    def get(self, user, path):
        self.client.force_login(user)
        return self.client.get(path, follow=False)

    def test_granted_page_is_reachable(self):
        self.assertEqual(self.get(self.user, "/employee/view-policies/").status_code, 200)

    def test_ungranted_catalogued_pages_are_refused(self):
        for path in [
            "/employee/employee-view/",
            "/employee/disciplinary-actions/",
            "/employee/document-request-view/",
            "/recruitment/pipeline/",
            "/recruitment/candidate-view/",
            "/leave/request-view/",
            "/leave/type-view/",
            "/pms/objective-list-view/",
            "/pms/feedback-view/",
            "/onboarding/onboarding-view/",
        ]:
            with self.subTest(path=path):
                response = self.get(self.user, path)
                self.assertEqual(response.status_code, 302, path)
                self.assertEqual(response["Location"], "/", path)

    def test_htmx_refusal_renders_the_404_partial(self):
        self.client.force_login(self.user)
        response = self.client.get("/employee/employee-view-card", HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"ABDELALI", response.content)

    def test_every_other_sidebar_page_is_refused(self):
        """A role ticking one page grants that page and nothing else in the menu."""
        for path in [
            "/employee/employee-profile/",
            "/employee/organisation-chart/",
            "/employee/company-documents/",
            "/employee/shift-request-view/",
            "/employee/work-type-request-view/",
            "/leave/user-request-view/",
            "/leave/leave-allocation-request-view/",
            "/leave/leave-dashboard",
            "/leave/view-compensatory-leave",
            "/pms/dashboard-view",
            "/pms/view-meetings/",
            "/pms/employee-bonus-point",
            "/onboarding/candidates-view/",
            "/recruitment/dashboard",
        ]:
            with self.subTest(path=path):
                self.assertEqual(self.get(self.user, path).status_code, 302, path)

    def test_the_home_page_is_never_refused(self):
        """It is where a refusal sends the holder back to, so it must not loop."""
        self.assertEqual(self.get(self.user, "/").status_code, 200)

    def test_self_service_pages_are_ticked_by_default_on_a_new_role(self):
        from base.forms import RoleForm
        from base.role_pages import DEFAULT_PAGES

        self.assertEqual(sorted(RoleForm().selected_pages()), sorted(DEFAULT_PAGES))

    def test_a_role_holding_the_defaults_keeps_its_self_service_pages(self):
        self.role.pages = {key: "view" for key in DEFAULT_PAGES}
        self.role.save()
        for path in ["/employee/employee-profile/", "/leave/user-request-view/"]:
            with self.subTest(path=path):
                self.assertEqual(self.get(self.user, path).status_code, 200, path)
        # still nothing beyond them
        self.assertEqual(
            self.get(self.user, "/employee/view-policies/").status_code, 302
        )

    def test_employee_without_a_role_is_not_restricted(self):
        response = self.get(self.free, "/employee/employee-view/")
        self.assertEqual(response.status_code, 200)

    def test_every_entry_the_sidebar_builds_is_catalogued(self):
        """
        Guards against menu entries reachable through an alternate URL.

        An `accessibility` callable may rewrite ``submenu["redirect"]`` at
        render time -- leave/sidebar.py:65 swaps the Congés dashboard for the
        employee one when the user lacks "leave.view_leaverequest". The
        rewritten URL is the one the holder clicks, so it is the one that has
        to be catalogued, and reading SUBMENUS without running the callables
        would not show it.

        The redirect is passed exactly as the sidebar leaves it, query string
        and all, because that is what the filtering in `horilla.config` sees.
        """
        from base.role_pages import pages_for_path

        self.client.force_login(self.user)
        menus = self.client.get("/employee/view-policies/").wsgi_request.MENUS
        uncatalogued = [
            (str(menu["menu"]), str(sub["menu"]), sub["redirect"])
            for menu in menus
            for sub in menu["submenu"]
            if not pages_for_path(str(sub["redirect"]))
        ]
        self.assertEqual(uncatalogued, [])

    def test_sidebar_hides_the_refused_entries(self):
        self.client.force_login(self.user)
        response = self.client.get("/employee/view-policies/")
        menus = response.wsgi_request.MENUS
        entries = {
            str(sub["menu"]) for menu in menus for sub in menu["submenu"]
        }
        self.assertIn("Règles internes", entries)
        self.assertNotIn("Employees", entries)
        self.assertNotIn("Actions disciplinaires", entries)
