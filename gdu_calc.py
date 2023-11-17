import requests
import math

# import geopandas
# from shapely.geometry import Point
import datetime
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    print("Event")
    print(event)

    print("Body:")
    body = json.loads(event["body"])
    print(body)

    start_date = body["start_date"]
    end_date = body["end_date"]
    lon = body["lon"]
    lat = body["lat"]
    base_number = 40
    upper_thresh = 86
    gdu = calc_gdu(
        start_date,
        end_date,
        lon,
        lat,
        base_number=base_number,
        upper_thresh=upper_thresh,
    )
    print(f"The gdu: {gdu}")

    logger.info(f"CloudWatch logs group: {context.log_group_name}")

    # return the calculated area as a JSON string
    data = {"gdu": gdu}
    return json.dumps(data)


# Look up stations
def get_stations():
    states = ["MN", "SD", "ND", "IA", "WI"]
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
def retrieve_station_data(stationid, start_date, end_date):
    interval = "dly"
    element = "AVA"
    reductions = "&reduction=".join(["max", "min", "avg"])

    url_station_collect = (
        "https://cli-dap.mrcc.purdue.edu/station/{stationid}/data?{query_string}"
    )
    headers = {"Accept": "application/json"}

    reductions = "avg"
    payload = "start={start_date}&end={end_date}&elem={element}&interval={interval}&reduction={reduction}".format(
        start_date=start_date,
        end_date=end_date,
        element=element,
        interval=interval,
        reduction=reductions,
    )
    # payload = "start={start_date}&end={end_date}&elem={element}".format(
    #     start_date=start_date,
    #     end_date=end_date,
    #     element=element,
    # )

    resp = requests.get(
        url_station_collect.format(stationid=stationid, query_string=payload),
        headers=headers,
    )
    resp = resp.json()
    if resp == {}:
        print("No data.")
        return None

    # What do nulls look like?

    return resp


# Calculate growing degree days
#   start_date (cover_crop_planting_date) as string %Y-%m-%d
#   end_date (photo_taken_date) as string %Y-%m-%d
#   long, lat (collectionpoint.coords) in EPSG:4326
def calc_gdu(start_date, end_date, lon, lat, base_number=40, upper_thresh=86):
    start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
    end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
    # Verify planting date is before photo date
    if end_date <= start_date:
        return None

    # gets all stations
    logging.info("About to get stations.")
    list_stations = get_stations()
    logging.info("Received " + str(len(list_stations)))
    # get df of distance to all stations
    logging.info("Calculating distance from point to all stations")
    list_stations = get_dist_to_stations(list_stations, lon, lat)
    logging.info("Closest station is:" + list_stations[0]["weabaseid"])

    attempt = 0
    while True:
        closest_station = list_stations[attempt]
        stationid = closest_station["weabaseid"]

        station_data = retrieve_station_data(
            stationid,
            start_date.strftime("%Y%m%d"),
            end_date.strftime("%Y%m%d"),
        )

        if station_data is None:
            attempt += 1
        else:
            break

    cumulative_gdd = 0
    for i in station_data:
        print("Before:", station_data[i]["AVA"])
        # Set NA in avg_temp to 0, what's this look like?
        # station_data[i]['AVA']

        # Set upper threshold to 86
        if station_data[i]["AVA"] > 86:
            station_data[i]["AVA"] = 86

        # subtract base number from avg temp
        station_data[i]["AVA"] = station_data[i]["AVA"] - base_number

        # Set less than 0 to 0
        if station_data[i]["AVA"] < 0:
            station_data[i]["AVA"] = 0

        print("After:", station_data[i]["AVA"])

        cumulative_gdd += station_data[i]["AVA"]

    return cumulative_gdd


"""
start_date = "2020-08-18"
end_date = "2021-04-19"
lon = -96.80417
lat = 45.5948

calc_gdu(start_date, end_date, lon, lat)
# 1561.416666
"""
