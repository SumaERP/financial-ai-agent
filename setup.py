from setuptools import setup, find_packages

setup(
    name="financial_bot",
    version="0.0.1",
    description="App de Gestion, Analysis y chatbot financiero",
    author="Quanta",
    author_email="osman@bequanta.com",
    packages=find_packages(),
    zip_safe=False,
    install_requires=["frappe"],
    include_package_data=True,
)