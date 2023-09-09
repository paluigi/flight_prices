# This script only run on the first and third wednesday in the month
# You can modify the function is_first_or_third_wednesday to change dates
from configparser import ConfigParser
import time
import os
from datetime import datetime, timedelta
import requests
from amadeus import Client, ResponseError
import pandas as pd
from save_minio import minio_upload


# Functions definition
def get_flight_prices(
    amadeus_client: Client,
    origin: str,
    destination: str,
    advance_days: int,
    stay_days: int,
    limit: int = 20,
) -> pd.DataFrame:
    """Function to get flight prices between origin and destination
    for a specific flight date. Return flights only. Maximum 20 options.

    Parameters:
    amadeus_client (amadeus.Client): client for Amadeus API
    origin (str): departure airport code, 3 capital letters
    destination (str): destination airport code, 3 capital letters
    advance_days (int): days before departure date
    stay_days (int): days between departure and return date
    limit (int): maximum number of flight offer to retrieve.

    Returns:
    pandas Dataframe with flight information and prices
    """
    flight_date = (datetime.now() + timedelta(days=advance_days)).strftime("%Y-%m-%d")
    return_date = (
        datetime.now() + timedelta(days=(advance_days + stay_days))
    ).strftime("%Y-%m-%d")
    try:
        # Individual flights
        flights = amadeus_client.shopping.flight_offers_search.get(
            originLocationCode=origin,
            destinationLocationCode=destination,
            departureDate=flight_date,
            returnDate=return_date,
            adults=1,
            nonStop="true",  # removing the non-stop requirement may raise errors.
            travelClass="ECONOMY",
            currencyCode="EUR",
            max=limit,
        ).data
        # Break the list in chunks of 5 to avoid errors
        flight_lists = [flights[i : i + 5] for i in range(0, len(flights), 5)]
        response_all_flights = []
        for f in flight_lists:
            time.sleep(1)
            # Try except block to overcome authentication issues. Maybe related to test environment
            try:
                response_all_flights.extend(
                    amadeus_client.shopping.flight_offers.pricing.post(f).data.get(
                        "flightOffers", []
                    )
                )
            except:
                continue
            # Price analysis
        analysis = amadeus_client.analytics.itinerary_price_metrics.get(
            originIataCode=origin,
            destinationIataCode=destination,
            departureDate=flight_date,
            currencyCode="EUR",
        )
        # Analysis data seems to have issues with some route. Probaly related to limited data in the test environment
        try:
            analysis_dict = {
                level.get("quartileRanking"): level.get("amount")
                for level in analysis.data[0].get("priceMetrics")
            }
        except:
            analysis_dict = {}
        results = []
        for flight in response_all_flights:
            results.append(
                {
                    "origin": origin,
                    "destination": destination,
                    "flight_date": flight_date,
                    "departure_time": flight.get("itineraries", [{}])[0]
                    .get("segments", [{}])[0]
                    .get("departure", {})
                    .get("at")[-8:],
                    "return_date": return_date,
                    "return_time": flight.get("itineraries", [{}])[-1]
                    .get("segments", [{}])[0]
                    .get("departure", {})
                    .get("at")[-8:],
                    "acquisition_date": datetime.now().strftime("%Y-%m-%d"),
                    "source": flight.get("source"),
                    "price": flight.get("price", {}).get("grandTotal"),
                    "net_price": flight.get("price", {}).get("base"),
                    "currency": flight.get("price", {}).get("currency"),
                    "carrier_outbound": flight.get("itineraries", [{}])[0]
                    .get("segments", [{}])[0]
                    .get("carrierCode"),
                    "flight_outbound": flight.get("itineraries", [{}])[0]
                    .get("segments", [{}])[0]
                    .get("number"),
                    "carrier_inbound": flight.get("itineraries", [{}])[-1]
                    .get("segments", [{}])[0]
                    .get("carrierCode"),
                    "flight_inbound": flight.get("itineraries", [{}])[-1]
                    .get("segments", [{}])[0]
                    .get("number"),
                    **analysis_dict,
                }
            )
        results_df = pd.DataFrame(results)
        return results_df
    # Logging exceptions without failing, return empty DataFrame
    except ResponseError as error:
        print(error)
        return pd.DataFrame({})
        # raise error
    except Exception as error:  # General catch for all other exceptions
        print(error)
        return pd.DataFrame({})
        # raise error


def is_first_or_third_wednesday():
    # Returns true if the execution date is the first
    # or third wednesday in the month
    today = datetime.today()
    # Check if today is a Wednesday and if it's the first or third Wednesday of the month
    if (
        today.weekday() == 2
    ):  # Wednesday corresponds to weekday() value 2 (0 = Monday, 1 = Tuesday, ...)
        day_of_month = today.day
        if 1 <= day_of_month <= 7 or 15 <= day_of_month <= 21:
            return True
    return False


# Script begin
# If not first or third wednesday, interrupt
if not is_first_or_third_wednesday():
    raise SystemExit(0)

config = ConfigParser()
config.read("amadeus.ini")
config_dict = {sect: dict(config.items(sect)) for sect in config.sections()}

# Instantiate client with secrets from config file
amadeus = Client(
    client_id=config["DEFAULT"]["amadeus_api_key"],
    client_secret=config["DEFAULT"]["amadeus_api_secret"],
    # comment line below while using sandbox
    # hostname='production' # Uncomment when using production API keys
)

# read list of origins and destinations
routes_df = pd.read_csv("flight_list.csv")


results = []
for route in routes_df.itertuples():
    # First advance window
    temp_df = get_flight_prices(
        amadeus_client=amadeus,
        origin=route.origin,
        destination=route.destination,
        advance_days=route.advance1,
        stay_days=route.stay_days,
        limit=20,
    )
    results.append(temp_df.copy())
    # Second advance window
    temp_df = get_flight_prices(
        origin=route.origin,
        destination=route.destination,
        advance_days=route.advance2,
        stay_days=route.stay_days,
        limit=20,
    )
    results.append(temp_df.copy())

data_df = pd.concat(results, ignore_index=True)
# Save file with current date in the name
file_name = "flight_prices_{}.csv".format(datetime.now().strftime("%Y-%m-%d"))
data_df.to_csv(file_name, index=False)

cloud_upload = minio_upload(config_dict, file_name, "CLOUD")
home_upload = minio_upload(config_dict, file_name, "HOME")

# Remove file if saved correctly
if cloud_upload and home_upload:
    os.remove(file_name)
else:
    # Move file to archive folder if not uploaded correctly
    os.rename(file_name, f"archive/{file_name}")

# Send scraping and upload status via Telegram
message = "Amadeus API - Flight prices.\nAcquired {} quotes.\nCloud Upload: {}\nHome upload: {}".format(
    data_df.shape[0], cloud_upload, home_upload
)
response = requests.post(
    url="https://api.telegram.org/bot{0}/{1}".format(
        config["TELEGRAM"]["token"], "sendMessage"
    ),
    data={"chat_id": config["TELEGRAM"].getint("chat_id"), "text": message},
).json()
