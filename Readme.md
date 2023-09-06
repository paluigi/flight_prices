# Amadeus API example
Version 1.0, 2023/09/05

This notebook provides an example about the use of API to retrieve price data.

Specifically, it uses [Amadeus Flight API](https://developers.amadeus.com/self-service/category/flights) to retrieve flight prices. At the date of writing (september 2023) Amadeus provides up to 2000 free calls for flight search every month. You will need to register on Amadeus website in order to get your API key, necessary to retrieve flight price data.

You can find more information about getting an Amadeus API key in their [FAQ](https://developers.amadeus.com/support/faq/?page=1&count=50), under "How do I get my Self-Service API key?".

If you use the Amadeus test environment, you may not be able to retrieve data on less common routes, as the data they make available for the test environment is a subset of the total data available. We suggest you to to use production API keys when retrieving data on specific routes.

You can run this notebook on your own environment, provided you install the Python packages listed in the requirements.txt file. You can also run this notebook on a cloud environment like Google Colab. In this case, you will have to follow specific directions in the cells below, uncommenting code as required. The minimum version of Python tested with this notebook is 3.9, we suggest at least 3.10 or newer.

There are two complementary files needed to run this notebook:

*   amadeus.ini: You should edit this file with your own API key details
*   flight_list.csv: You should insert in this files the routes for which you want to retrieve prices.

The notebook is structured assuming you have those two files in the same folder as the notebook. In case you prefer a different structure, you should adjust the paths to those files accordingly in the cells below.

The file flight_list.csv has the following columns:

*   origin: IATA 3-letter airport code for flight departure
*   destination: IATA 3-letter airport code for flight arrival
*   stay_days: How many days between outbound and return flight
*   advance1: How many days after the current date you want to depart (1st search)
*   advance2: How many days after the current date you want to depart (2nd search)

You can search IATA 3-letter codes on their [official website](https://www.iata.org/en/publications/directories/code-search/).

There are two searches at different time horizons (advance1 and advance2), as this is common practice in several National Statistic Organization. If you only want to retrieve prices with a single time horizon, you can modify the script accordingly.