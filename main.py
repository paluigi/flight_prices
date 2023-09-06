from configparser import ConfigParser
import time
from datetime import datetime, timedelta
from amadeus import Client, ResponseError
import pandas as pd


config = ConfigParser()
config.read('amadeus.ini')

# Instantiate client with secrets from config file
amadeus = Client(
    client_id=config["DEFAULT"]["amadeus_api_key"],
    client_secret=config["DEFAULT"]["amadeus_api_secret"]
)

# read list of origins and destinations
routes_df = pd.read_csv("flight_list.csv")


def get_flight_prices(origin: str, destination: str, advance_days: int, stay_days: int, limit: int = 20) -> pd.DataFrame:
    """Function to get flight prices between origin and destination
    for a specific flight date. Return flights only. Maximum 20 options.

    Parameters:
    origin (str): departure airport code, 3 capital letters
    destination (str): destination airport code, 3 capital letters
    advance_days (int): days before departure date
    stay_days (int): days between departure and return date
    limit (int): maximum number of flight offer to retrieve.

    Returns:
    pandas Dataframe with flight information and prices
    """
    flight_date = (datetime.now() + timedelta(days=advance_days)).strftime("%Y-%m-%d")
    return_date = (datetime.now() + timedelta(days=(advance_days + stay_days))).strftime("%Y-%m-%d")
    try:
        # Individual flights
        flights = amadeus.shopping.flight_offers_search.get(originLocationCode=origin,
                                                            destinationLocationCode=destination,
                                                            departureDate=flight_date,
                                                            returnDate=return_date,
                                                            adults=1,
                                                            nonStop="true",  # removing the non-stop requirement may raise errors.
                                                            travelClass="ECONOMY",
                                                            currencyCode="EUR",
                                                            max=limit).data
        # Break the list in chunks of 5 to avoid errors
        flight_lists = [flights[i:i + 5] for i in range(0, len(flights), 5)]
        response_all_flights = []
        for f in flight_lists:
            time.sleep(1)
            # Try except block to overcome authentication issues. Maybe related to test environment
            try:
                response_all_flights.extend(amadeus.shopping.flight_offers.pricing.post(f).data.get("flightOffers", []))
            except:
                continue
            # Price analysis
        analysis = amadeus.analytics.itinerary_price_metrics.get(
            originIataCode=origin,
            destinationIataCode=destination,
            departureDate=flight_date,
            currencyCode="EUR"
        )
        # Analysis data seems to have issues with some route. Probaly related to limited data in the test environment
        try:
            analysis_dict = {level.get("quartileRanking"): level.get("amount") for level in analysis.data[0].get("priceMetrics")}
        except:
            analysis_dict = {}
        results = []
        for flight in response_all_flights:
            results.append(
            {
                "origin": origin,
                "destination": destination,
                "flight_date": flight_date,
                "departure_time": flight.get("itineraries", [{}])[0].get("segments", [{}])[0].get("departure", {}).get("at")[-8:],
                "return_date": return_date,
                "return_time": flight.get("itineraries", [{}])[-1].get("segments", [{}])[0].get("departure", {}).get("at")[-8:],
                "acquisition_date": datetime.now().strftime("%Y-%m-%d"),
                "source": flight.get("source"),
                "price": flight.get("price", {}).get("grandTotal"),
                "net_price": flight.get("price", {}).get("base"),
                "currency": flight.get("price", {}).get("currency"),
                "carrier_outbound": flight.get("itineraries", [{}])[0].get("segments", [{}])[0].get("carrierCode"),
                "flight_outbound": flight.get("itineraries", [{}])[0].get("segments", [{}])[0].get("number"),
                "carrier_inbound": flight.get("itineraries", [{}])[-1].get("segments", [{}])[0].get("carrierCode"),
                "flight_inbound": flight.get("itineraries", [{}])[-1].get("segments", [{}])[0].get("number"),
                **analysis_dict
            }
        )       
        results_df = pd.DataFrame(results)
        return results_df

    # Logging exceptions without failing, return empty DataFrame
    except ResponseError as error:
        print(error)
        return pd.DataFrame({})
        #raise error
    except Exception as error:  # General catch for all other exceptions
        print(error)
        return pd.DataFrame({})
        #raise error


results = []
for route in routes_df.itertuples():
    # First advance window
    temp_df = get_flight_prices(
        origin = route.origin,
        destination = route.destination,
        advance_days = route.advance1,
        stay_days = route.stay_days,
        limit = 20)
    results.append(temp_df.copy())
    # Second advance window
    temp_df = get_flight_prices(
        origin = route.origin,
        destination = route.destination,
        advance_days = route.advance2,
        stay_days = route.stay_days,
        limit = 20)
    results.append(temp_df.copy())

data_df = pd.concat(results, ignore_index=True)
# Save file with current date in the name
data_df.to_csv("flight_prices_{}.csv".format(datetime.now().strftime("%Y-%m-%d")), index=False)
