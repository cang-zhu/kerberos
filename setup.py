from setuptools import setup, find_packages

setup(
    name="kerberos-auth",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'flask==2.0.1',
        'pyotp==2.6.0',
        'requests==2.26.0',
        'cryptography==3.4.7',
        'python-dotenv==0.19.0',
        'gunicorn==20.1.0',
        'flask-sqlalchemy==2.5.1',
        'werkzeug==2.0.1',
        'flask-migrate==3.1.0',
        'alembic==1.7.1'
    ],
) 