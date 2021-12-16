from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in project_payroll/__init__.py
from project_payroll import __version__ as version

setup(
	name="project_payroll",
	version=version,
	description="this app for make payroll for employee based on projects ",
	author="Ibrahim Morghim",
	author_email="morghim@outlook.sa",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
