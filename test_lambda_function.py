import requests
import sys


def test_lambda_function(lambda_url):
    start_date = "2020-08-18"
    end_date = "2021-04-19"
    lon = -96.80417
    lat = 45.5948

    headers = {"Accept": "application/json"}

    data = {
        "target": "GDU",
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

    return resp


if __name__ == "__main__":
    expected = {
        "statusCode": 200,
        "statusDescription": "200 OK",
        "isBase64Encoded": False,
        "headers": {"Content-Type": "text/json; charset=utf-8"},
        "body": {
            "dist_to_station_km": 16.728011016930733,
            "stationid": "K8D3",
            "cumulative_gdd": 1713.9054838176935,
            "start_date": "2020-08-18",
            "end_date": "2021-04-19",
            "lon": -96.80417,
            "lat": 45.5948,
        },
    }

    lambda_url = sys.argv[1]
    lambda_url = lambda_url.replace('"', "")
    # print(lambda_url)
    result = test_lambda_function(lambda_url)

    print(result == expected)
