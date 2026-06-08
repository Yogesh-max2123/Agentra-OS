import requests
import datetime
import os


def get_live_train_status(train_number: str, dep_date_str: str = None):
    """
    Fetches real-time train status from RapidAPI.
    dep_date_str should be in YYYYMMDD format.
    """
    if not dep_date_str:

        dep_date_str = datetime.datetime.now().strftime("%Y%m%d")

    url = "https://indian-railway-irctc.p.rapidapi.com/api/trains/v1/train/status"

    querystring = {
        "departure_date": dep_date_str,
        "isH5": "true",
        "client": "web",
        "deviceIdentifier": "Mozilla Firefox-138.0",
        "train_number": train_number,
    }

    headers = {
        "x-rapidapi-key": os.getenv("RAPIDAPI_TRAIN_STATUS_API_KEY"),
        "x-rapidapi-host": "indian-railway-irctc.p.rapidapi.com",
        "Content-Type": "application/json",
    }

    try:
        response = requests.get(url, headers=headers, params=querystring)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"Railway API Error: {e}")
        return None


def calculate_origin_date(
    train_number: str, journey_details: str, travel_date: str
) -> str:
    """
    Backend internal function to calculate actual train origin date based on DayCount.
    """
    try:

        source_station = ""
        if " from " in journey_details and " to " in journey_details:
            source_station = (
                journey_details.split(" from ")[1].split(" to ")[0].strip().lower()
            )

        today_str = datetime.now().strftime("%Y%m%d")
        route_data = get_live_train_status(train_number, today_str)

        day_count = 1

        if route_data and "body" in route_data and "stations" in route_data["body"]:
            for stn in route_data["body"]["stations"]:

                stn_name = stn.get("stationName", "").lower()
                stn_code = stn.get("stationCode", "").lower()

                if source_station == stn_name or source_station == stn_code:
                    day_count = int(stn.get("dayCount", 1))
                    break

        base_dt = (
            datetime.strptime(travel_date, "%Y-%m-%d")
            if travel_date
            else datetime.now()
        )
        origin_dt = base_dt - datetime.timedelta(days=day_count - 1)

        return origin_dt.strftime("%Y%m%d")

    except Exception as e:
        print(f"Origin Date Calculation Error: {e}")

        if travel_date:
            return travel_date.replace("-", "")
        return datetime.now().strftime("%Y%m%d")
