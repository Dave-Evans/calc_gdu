# Code for calculating GDU 

These are instructions and breadcrumbs for creating a lambda function on AWS to calculate
growing degree units and precipitation for my web apps.

It pulls daily min and max air temperature from the [Climate Data Access Portal](https://mrcc.purdue.edu/data_serv/cli-dap)
and calculates growing degree units using the Baskerville-Emin method.

It takes a start date, end date, and a longitude and latitude value.
The lon and lat are used to find the nearest weather station to provide the data.
If a weather station has greater than 5% missing data for that time period then the next closest station is used.
The weather station id and distance in kilometers are returned in the request.

Currently not supporting precip calculation.


For using the service with cURL
```bash
# Madison GDU for summer 2023: 2883
curl -v 'https://gncpnwkl6ewrm66haprvfb7bpa0aovcv.lambda-url.us-east-2.on.aws/' \
-H 'content-type: application/json' \
-d '{ "lon": -89.2988646, "lat": 43.0899635, "start_date": "2023-06-21", "end_date": "2023-09-21"}'

# For testing another location
curl -v 'https://gncpnwkl6ewrm66haprvfb7bpa0aovcv.lambda-url.us-east-2.on.aws/' \
-H 'content-type: application/json' \
-d '{ "lon": -96.80417, "lat": 45.5948, "start_date": "2020-08-18", "end_date": "2021-04-19"}'
```

For accessing with Python:
```python
import requests
start_date = "2020-08-18"
end_date = "2021-04-19"
lon = -96.80417
lat = 45.5948

headers = {"Accept": "application/json"}

data = {
    "lon": -96.80417,
    "lat": 45.5948,
    "start_date": "2020-08-18",
    "end_date": "2021-04-19",
}

resp = requests.get(
    lambda_url,
    headers=headers,
    data=data,
)
resp = resp.json()
```

For R
```R
library(httr)
library(jsonlite)

lambda_url = 'https://gncpnwkl6ewrm66haprvfb7bpa0aovcv.lambda-url.us-east-2.on.aws/'
rslt = POST(lambda_url, body = list(
  lon=-89.2988646,
  lat=43.0899635,
  start_date='2023-06-21',
  end_date='2023-09-21'
),
encode="json"
)

# For the response
content(rslt)

# The body of the response
content(rslt)$body

# The cumulative growing degree days
content(rslt)$body$cumulative_gdd
```

## Setup up notes

I'm creating a separate repository from main web app.
`mkdir calc_gdu`

Get latest(?) version of python for lambda compatibility.
Create a virtual environment and install `requests`

```bash
sudo apt update
sudo apt install python3.11
sudo apt install python3.11-dev python3.11-venv
python3.11 -m venv denv
source denv/bin/activate
pip install requests # geopandas

cd denv/lib/python3.11/site-packages
zip -r ../../../../dep_pkg.zip .

cd ../../../..
zip dep_pkg.zip gdu_calc.py
```

Terraform is pretty straightforward for setting up a lambda funcation.

 - AWS IAM Policy document
 - IAM role
 - IAM role policy attachment
 - Build lambda url
 - Lambda function
 - Setup logging to cloudwatch


Makefile has been built to setup Lambda function and url and to test function.

```bash
make
```

This will create the virt env
    install the requests module
    zip up site packages and script
    use terraform to create the lambda

```bash
make test
```
Will confirm the output is as it should be

```bash
make clean
```
Will tear it all down.


### Sources

https://docs.aws.amazon.com/lambda/latest/dg/python-package.html
https://nquayson.com/aws-lambda-function-url-using-terraform-quick-walkthrough
https://callaway.dev/deploy-python-lambdas-with-terraform/
