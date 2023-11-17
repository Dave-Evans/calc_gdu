# Creating an AWS Lambda Function for Growing Degree Days and Precip

Instructions and breadcrumbs for creating a lambda function on AWS to calculate
growing degree units and precipitation for my web apps.

## Setup up

I'm creating a separate repository from main web app.
`mkdir calc_gdu`

Get latest(?) version of python for lambda compatibility.
Create a virtual environment and install `requests` and `geopandas`.

```bash
sudo apt update
sudo apt install python3.11
sudo apt install python3.11-dev python3.11-venv
python3.11 -m venv lenv
source lenv/bin/activate
pip install requests geopandas
```



### Sources

https://docs.aws.amazon.com/lambda/latest/dg/python-package.html
