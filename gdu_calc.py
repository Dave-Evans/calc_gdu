import requests
import math

# import geopandas
# from shapely.geometry import Point
import datetime
import json
import logging
import base64

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    print("Event")
    print(event)

    body = event["body"]
    print("Body before:")
    print(body)
    if event["isBase64Encoded"]:
        body = decode_body(body)
    else:
        body = json.loads(body)

    print("Body after:")
    print(body)

    start_date = body["start_date"]
    end_date = body["end_date"]

    # Verify planting date is before photo date
    if end_date <= start_date:
        return None

    lon = float(body["lon"])
    lat = float(body["lat"])
    base_number = 40
    upper_thresh = 86
    result = calc_gdu(
        start_date,
        end_date,
        lon,
        lat,
        base_number=base_number,
        upper_thresh=upper_thresh,
    )

    logger.info(result)

    logger.info(f"CloudWatch logs group: {context.log_group_name}")

    response = {
        "statusCode": 200,
        "statusDescription": "200 OK",
        "isBase64Encoded": False,
        "headers": {"Content-Type": "text/json; charset=utf-8"},
        "body": result,
    }
    # return the calculated area as a JSON string

    return json.dumps(response)


def decode_body(body):
    """For decoding base64 encoded body to dict
    body of the form:
    'bG9uPS05Ni44MDQxNyZsYXQ9NDUuNTk0OCZzdGFydF9kYXRlPTIwMjAtMDgtMTgmZW5kX2RhdGU9MjAyMS0wNC0xOQ=='
    """
    body = base64.b64decode(body).decode()
    split_body = body.split("&")
    dct_body = {}
    for i in split_body:
        dct_body[i.split("=")[0]] = i.split("=")[1]

    return dct_body


# Look up stations
def get_stations():
    states = ["MN", "SD", "ND", "IA", "WI", "IL", "MI"]
    url_station_collect = "https://cli-dap.mrcc.purdue.edu/state/{state}/"
    headers = {"Accept": "application/json"}

    list_stations = []
    for state in states:
        resp = requests.get(url_station_collect.format(state=state), headers=headers)
        resp = resp.json()
        list_stations.extend(resp)

    # convert to geospatial
    # df_stations = geopandas.pd.DataFrame(list_stations)
    # df_stations = geopandas.GeoDataFrame(
    #     df_stations,
    #     geometry=geopandas.points_from_xy(
    #         df_stations.stationlongitude, df_stations.stationlatitude
    #     ),
    #     crs=4326,
    # )

    return list_stations


def calc_dist(lon1, lat1, lon2, lat2):
    """For calculating the distance between two points
    powerappsguide.com/blog/post/formulas-calculate-the-distance-between-2-points-longitude-latitude
    returns distance in km
    """
    r = 6371  # radius of Earth (KM)
    p = 0.017453292519943295  # Pi/180
    a = (
        0.5
        - math.cos((lat2 - lat1) * p) / 2
        + math.cos(lat1 * p)
        * math.cos(lat2 * p)
        * (1 - math.cos((lon2 - lon1) * p))
        / 2
    )

    d = 2 * r * math.asin(math.sqrt(a))  # 2*R*asin

    return d


# find nearest station to covercrop location
def get_dist_to_stations(list_stations, lon, lat):
    """Calculate distance to point from each station"""
    for station in list_stations:
        station["distance"] = calc_dist(
            station["stationlongitude"], station["stationlatitude"], lon, lat
        )

    # sort by distance, smallest to largest
    list_stations = sorted(list_stations, key=lambda d: d["distance"])

    return list_stations


# collect data from that station
def retrieve_station_data(
    stationid, start_date, end_date, element="AVA", reductions="avg"
):
    interval = "dly"
    # Precip
    # element = "PRE"
    # Average Air Temp
    # element = "AVA"
    # element = "&elem=".join(["AVA", "PRE"])
    # reductions = "avg"
    if isinstance(element, list):
        element = "&elem=".join(element)

    url_station_collect = (
        "https://cli-dap.mrcc.purdue.edu/station/{stationid}/data?{query_string}"
    )
    headers = {"Accept": "application/json"}

    payload = "start={start_date}&end={end_date}&elem={element}&interval={interval}&reduction={reduction}".format(
        start_date=start_date,
        end_date=end_date,
        element=element,
        interval=interval,
        reduction=reductions,
    )

    resp = requests.get(
        url_station_collect.format(stationid=stationid, query_string=payload),
        headers=headers,
    )
    resp = resp.json()
    if resp == {}:
        print("No data.")
        return None

    # What do nulls look like?
    null_count = 0
    for i in resp:
        try:
            resp[i]["AVA"] = float(resp[i]["AVA"])
        except ValueError:
            null_count += 1
            resp[i]["AVA"] = 0

    prop_missing = null_count / len(resp)
    logging.info("Null count: " + str(prop_missing))
    if prop_missing > 0.05:
        logging.info("Missing too many from this station.")
        return None

    return resp


def get_min_max_ava(list_stations, start_date, end_date):
    """Get the min and max air temp for each day.
    Testing the station data for missing data. If missing prop
    greater than 0.05 then discard and move to next nearest station.
        list_stations: list of"""
    attempt = 0
    while True:
        logging.info(f"Attempt no. {attempt}")
        closest_station = list_stations[attempt]
        stationid = closest_station["weabaseid"]
        logging.info(f"Pulling data from: {stationid}")

        max_station_data = retrieve_station_data(
            stationid,
            start_date.strftime("%Y%m%d"),
            end_date.strftime("%Y%m%d"),
            reductions="max",
        )

        min_station_data = retrieve_station_data(
            stationid,
            start_date.strftime("%Y%m%d"),
            end_date.strftime("%Y%m%d"),
            reductions="min",
        )
        if (min_station_data is None) | (max_station_data is None):
            logging.info("No data found.")
            attempt += 1
        else:
            break

    # Combine min and max returns to
    if len(max_station_data) != len(min_station_data):
        print("####################")
        print("Different length for min and max temp data")
        print("####################")
        raise Exception("Different length for min and max temp data")

    station_data = {}
    for i in max_station_data:
        station_data[i] = {
            "min_temp": min_station_data[i]["AVA"],
            "max_temp": max_station_data[i]["AVA"],
        }

    return station_data, stationid, closest_station["distance"]


def calcHeat(fk1, tsum, diff):
    twopi = 6.283185308
    pihlf = 1.570796327
    d2 = fk1 - tsum
    theta = math.atan(d2 / math.sqrt(diff * diff - d2 * d2))
    if (d2 < 0) & (theta > 0):
        theta = theta - math.pi

    return (diff * math.cos(theta) - d2 * (pihlf - theta)) / twopi


def gdu_be(station_data, start_date, end_date, base_number=40, upper_thresh=86):
    """For calculating the GDU with the BE method"""

    heat = 0
    fk1 = 2 * base_number

    cumulative_gdd = 0
    for i in station_data:
        tmin = station_data[i]["min_temp"]
        tmax = station_data[i]["max_temp"]

        diff = tmax - tmin
        tsum = tmax + tmin

        # return 0 if invalid inputs or max below base_number
        if (tmin > tmax) | (tmax <= tmin) | (tmax <= base_number):
            gdu = 0
        elif tmin >= base_number:
            gdu = (tsum - fk1) / 2
        elif tmin < base_number:
            gdu = calcHeat(fk1, tsum, diff)
        elif tmax > upper_thresh:
            fk1 = 2 * upper_thresh
            zheat = heat
            heat = calcHeat(fk1, tsum, diff)
            gdu = zheat - 2 * heat

        cumulative_gdd += gdu

    return cumulative_gdd


# Calculate growing degree days
#   start_date (cover_crop_planting_date) as string %Y-%m-%d
#   end_date (photo_taken_date) as string %Y-%m-%d
#   long, lat (collectionpoint.coords) in EPSG:4326
def calc_gdu(start_date, end_date, lon, lat, base_number=40, upper_thresh=86):
    try:
        start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
    except ValueError as err:
        logging.error(f"Unexpected {err=}, {type(err)=}")
        return {"error": str(err)}

    try:
        end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError as err:
        logging.error(f"Unexpected {err=}, {type(err)=}")
        return {"error": err}

    # gets all stations
    logging.info("About to get stations.")
    list_stations = get_stations()
    logging.info("Received " + str(len(list_stations)))
    # get df of distance to all stations
    logging.info("Calculating distance from point to all stations")
    list_stations = get_dist_to_stations(list_stations, lon, lat)

    station_data, stationid, distance = get_min_max_ava(
        list_stations, start_date, end_date
    )

    cumulative_gdd = gdu_be(
        station_data, start_date, end_date, base_number=40, upper_thresh=86
    )

    # Result object to return
    result = {
        "dist_to_station_km": distance,
        "stationid": stationid,
        "cumulative_gdd": cumulative_gdd,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "lon": lon,
        "lat": lat,
    }

    return result


"""
start_date = "2020-08-18"
end_date = "2021-04-19"
lon = -96.80417
lat = 45.5948

calc_gdu(start_date, end_date, lon, lat)
# 1561.416666
"""
