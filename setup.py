from setuptools import setup, find_packages

setup(
	name="financial_bot",
	version="0.0.1",
	packages=find_packages(),
	include_package_data=True,
	zip_safe=False,
	install_requires=["frappe"],
)
