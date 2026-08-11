from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from hr.models import Employee


class EmployeeDeletionAuthTests(TestCase):
	def setUp(self):
		self.admin = User.objects.create_superuser(
			username='admin',
			email='admin@example.com',
			password='AdminPass123!',
		)
		self.employee_user = User.objects.create_user(
			username='emp.login',
			email='emp@example.com',
			password='EmployeePass123!',
		)
		self.employee = Employee.objects.create(
			name='Employee User',
			email='emp@example.com',
			role='employee',
			user=self.employee_user,
		)

	def test_single_employee_delete_disables_linked_user_login(self):
		self.client.force_login(self.admin)

		response = self.client.get(reverse('employee_delete', args=[self.employee.pk]))

		self.assertEqual(response.status_code, 302)
		self.assertFalse(Employee.objects.filter(pk=self.employee.pk).exists())

		self.employee_user.refresh_from_db()
		self.assertFalse(self.employee_user.is_active)
		self.assertFalse(self.employee_user.has_usable_password())

		self.client.logout()
		can_login = self.client.login(username='emp.login', password='EmployeePass123!')
		self.assertFalse(can_login)

	def test_bulk_employee_delete_disables_linked_user_login(self):
		second_user = User.objects.create_user(
			username='emp.second',
			email='emp2@example.com',
			password='EmployeePass456!',
		)
		second_employee = Employee.objects.create(
			name='Second Employee',
			email='emp2@example.com',
			role='employee',
			user=second_user,
		)

		self.client.force_login(self.admin)
		response = self.client.post(
			reverse('employee_list'),
			{
				'bulk_action': 'delete',
				'selected_employees': [str(self.employee.pk), str(second_employee.pk)],
			},
		)

		self.assertEqual(response.status_code, 302)
		self.assertFalse(Employee.objects.filter(pk__in=[self.employee.pk, second_employee.pk]).exists())

		self.employee_user.refresh_from_db()
		second_user.refresh_from_db()
		self.assertFalse(self.employee_user.is_active)
		self.assertFalse(second_user.is_active)

