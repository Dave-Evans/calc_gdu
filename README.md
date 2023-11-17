# Creating an AWS Lambda Function for Growing Degree Days and Precip

Instructions and breadcrumbs for creating a lambda function on AWS to calculate
growing degree units and precipitation for my web apps.

## Setup up

I'm creating a separate repository from main web app.
`mkdir calc_gdu`

Get latest(?) version of python for lambda compatibility.
Create a virtual environment and install `requests` # and `geopandas`.

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


For testing lambda
```bash
curl -v 'https://c76d5gzlin46g55ymdroqm24lu0efpnp.lambda-url.us-east-2.on.aws/' \
-H 'content-type: application/json' \
-d '{ "lon": -96.80417, "lat": 45.5948, "start_date": "2020-08-18", "end_date": "2021-04-19"}'

# 2785
curl -v 'https://c76d5gzlin46g55ymdroqm24lu0efpnp.lambda-url.us-east-2.on.aws/' \
-H 'content-type: application/json' \
-d '{ "lon": -89.2988646, "lat": 43.0899635, "start_date": "2020-06-21", "end_date": "2020-09-21"}'

# 2886.8
curl -v 'https://c76d5gzlin46g55ymdroqm24lu0efpnp.lambda-url.us-east-2.on.aws/' \
-H 'content-type: application/json' \
-d '{ "lon": -89.2988646, "lat": 43.0899635, "start_date": "2021-06-21", "end_date": "2021-09-21"}'

# 2922
curl -v 'https://c76d5gzlin46g55ymdroqm24lu0efpnp.lambda-url.us-east-2.on.aws/' \
-H 'content-type: application/json' \
-d '{ "lon": -89.2988646, "lat": 43.0899635, "start_date": "2022-06-21", "end_date": "2022-09-21"}'

# 2883
curl -v 'https://c76d5gzlin46g55ymdroqm24lu0efpnp.lambda-url.us-east-2.on.aws/' \
-H 'content-type: application/json' \
-d '{ "lon": -89.2988646, "lat": 43.0899635, "start_date": "2023-06-21", "end_date": "2023-09-21"}'


```



### Sources

https://docs.aws.amazon.com/lambda/latest/dg/python-package.html
