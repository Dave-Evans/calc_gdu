import requests
import geopandas
from shapely.geometry import Point
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

    start_date = body["start_date"]
    end_date = body["end_date"]
    lon = body["lon"]
    lat = body["lat"]
    base_number = 40
    upper_thresh = 86
    gdu = calc_gdu(start_date, end_date, lon, lat, base_number=40, upper_thresh=86)
    print(f"The area is {gdu}")

    logger.info(f"CloudWatch logs group: {context.log_group_name}")

    # return the calculated area as a JSON string
    data = {"area": area}
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
    df_stations = geopandas.pd.DataFrame(list_stations)
    df_stations = geopandas.GeoDataFrame(
        df_stations,
        geometry=geopandas.points_from_xy(
            df_stations.stationlongitude, df_stations.stationlatitude
        ),
        crs=4326,
    )

    return df_stations


# find nearest station to covercrop location
def get_dist_to_stations(df_stations, df_collection):
    df_stations = df_stations.to_crs(epsg=5070)

    ## duplication records in collection to work with
    ##  distance function
    dupe_collection = df_collection.copy()
    for i in range(1, len(df_stations)):
        dupe_collection = geopandas.pd.concat([dupe_collection, df_collection])
    dupe_collection = dupe_collection.to_crs(epsg=5070)

    dupe_collection.reset_index(inplace=True, drop=True)
    dist = dupe_collection.distance(df_stations, align=True)
    dist.name = "distance"
    df_station_distance = df_stations.join(dist)
    df_station_distance.sort_values("distance", inplace=True)

    return df_station_distance


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
    # payload = "start={start_date}&end={end_date}&elem={element}&interval={interval}&reduction={reduction}".format(
    #     start_date=start_date,
    #     end_date=end_date,
    #     element=element,
    #     interval=interval,
    #     reduction=reductions,
    # )
    payload = "start={start_date}&end={end_date}&elem={element}".format(
        start_date=start_date,
        end_date=end_date,
        element=element,
    )

    resp = requests.get(
        url_station_collect.format(stationid=stationid, query_string=payload),
        headers=headers,
    )
    resp = resp.json()
    if resp == {}:
        print("No data.")
        return None
    df = geopandas.pd.DataFrame(resp).transpose()

    df.AVA = geopandas.pd.to_numeric(df.AVA, errors="coerce")

    prop_missing = df.AVA.isna().sum() / len(df)
    # print(f"{round(prop_missing,3) *100} missing")

    if prop_missing > 0.05:
        return None

    df["collect_time"] = geopandas.pd.to_datetime(df.index, format="%Y%m%d%H%M")

    grpd = df.groupby(geopandas.pd.Grouper(key="collect_time", axis=0, freq="D")).agg(
        min_temp=geopandas.pd.NamedAgg(column="AVA", aggfunc="min"),
        max_temp=geopandas.pd.NamedAgg(column="AVA", aggfunc="max"),
        avg_temp=geopandas.pd.NamedAgg(column="AVA", aggfunc="mean"),
        count_obs=geopandas.pd.NamedAgg(column="AVA", aggfunc="count"),
    )

    return grpd


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

    df_collection = geopandas.GeoDataFrame(
        {
            # "photo_taken_date": [datetime.date(2022, 6, 6)],
            # "cover_crop_planting_date": [datetime.date(2021, 10, 4)],
            # "geometry": [Point((-96.55012607574463, 45.8826454738681))],
            "photo_taken_date": [end_date],
            "cover_crop_planting_date": [start_date],
            "geometry": [Point(lon, lat)],
        },
        crs=4326,
    )

    # gets all stations
    df_stations = get_stations()

    # get df of distance to all stations
    df_station_distance = get_dist_to_stations(df_stations, df_collection)

    attempt = 0
    while True:
        closest_station = df_station_distance.iloc[attempt]
        stationid = closest_station.weabaseid

        df_station_data = retrieve_station_data(
            stationid,
            start_date.strftime("%Y%m%d"),
            end_date.strftime("%Y%m%d"),
        )

        if df_station_data is None:
            attempt += 1
        else:
            break

    # If avg_temp is NA
    # then set to 0 (this was screwing up the following where statement)
    df_station_data.avg_temp = df_station_data.avg_temp.where(
        ~geopandas.pd.isna(df_station_data.avg_temp), 0
    )

    # If greater than upper_thresh (86), set to upper_thresh (86)
    df_station_data.avg_temp = df_station_data.avg_temp.where(
        df_station_data.avg_temp < upper_thresh, upper_thresh
    )

    gdd = df_station_data.avg_temp - base_number

    # Where greater or equal to 0 keep; otherwise replace with 0
    gdd.where(gdd >= 0, 0, inplace=True)

    cumulative_gdd = gdd.sum()

    return cumulative_gdd


"""
start_date = "2020-08-18"
end_date = "2021-04-19"
lon = -96.80417
lat = 45.5948

calc_gdu(start_date, end_date, lon, lat)
# 1561.416666
"""
