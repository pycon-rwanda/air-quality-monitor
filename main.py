# main.py
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import gradio as gr
import requests
import os
from dotenv import load_dotenv
import time

# Load environment variables from .env file
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Define API keys
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")


@app.get("/")
def read_root():
    """
    The root endpoint of the API, returns a welcome message.

    Returns:
    -------
    dict
        A dictionary with a message key containing a welcome message.
    """
    return {"message": "Welcome to the Air Quality Monitor"}


def geocode_location(location: str) -> tuple[float, float] | None:
    """Get latitude and longitude from location name using OpenWeather Geocoding API.

    Args:
    location (str): The location name to be searched.

    Returns:
    tuple[float, float] | None: The latitude and longitude of the location. If the location
    could not be found, returns None.
    """
    # Construct the URL for the API call
    geocode_url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid=b3789908d94f6e8732447989b53907f9"
    # Make the API call
    response = requests.get(geocode_url)

    # Check if the call was successful
    if response.status_code == 200:
        # Get the data from the response
        data = response.json()
        # Extract the latitude and longitude from the data
        lat = data["coord"]["lat"]
        lon = data["coord"]["lon"]
        print(lat, lon)
        # Return the coordinates
        return lat, lon
    else:
        # If the call was unsuccessful, return None
        return None


def get_air_quality(location):
    """Fetch air quality data from OpenWeather API using latitude and longitude.

    Args:
        location (str): The location name to be searched.

    Returns:
        dict: A dictionary with the location name, Air Quality Index (AQI) and
        health advisory.
        If the location could not be found, returns a dictionary with an
        "error" key containing an error message.
    """
    # Get the latitude and longitude of the location
    coords = geocode_location(location)

    if coords is None:
        # Return an error message if the location could not be found
        return {
            "error": "Could not fetch location coordinates. Please check the location name."
        }

    # Extract the latitude and longitude from the coordinates
    lat, lon = coords

    # Construct the URL for the API call
    aqi_url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid=b3789908d94f6e8732447989b53907f9"

    # Make the API call
    response = requests.get(aqi_url)

    # Check if the call was successful
    if response.status_code == 200:
        # Get the data from the response
        data = response.json()
        # Extract the AQI and health advisory from the data
        aqi = data["list"][0]["main"]["aqi"]
        advisory = get_health_advisory(aqi)
        # Return the AQI and health advisory
        return {"location": location, "aqi": aqi, "advisory": advisory}
    elif response.status_code == 429:  # Rate limit reached
        retry_after = int(response.headers.get('Retry-After', 10))
        print(f"Rate limit reached. Retrying in {retry_after} seconds...")
        time.sleep(retry_after)  # Wait for the retry period
    else:
        # If the call was unsuccessful, return an error message
        return {"error": "Could not fetch air quality data."}


def get_health_advisory(aqi):
    """
    Return health advisory based on AQI levels.

    The health advisory is based on the Air Quality Index (AQI) levels as follows:

    * Good: Air quality is satisfactory.
    * Moderate: Air quality is acceptable.
    * Unhealthy for Sensitive Groups: Some members may experience health effects.
    * Unhealthy: Everyone may experience health effects.
    * Very Unhealthy: Health alert for everyone.
    * Hazardous: Health warning of emergency conditions.

    Args:
        aqi (int): The Air Quality Index (AQI) level.

    Returns:
        str: The health advisory message.
    """
    if aqi == 1:
        # Good: Air quality is satisfactory
        return "Good: Air quality is satisfactory."
    elif aqi == 2:
        # Moderate: Air quality is acceptable
        return "Moderate: Air quality is acceptable."
    elif aqi == 3:
        # Unhealthy for Sensitive Groups: Some members may experience health effects
        return "Unhealthy for Sensitive Groups: Some members may experience health effects."
    elif aqi == 4:
        # Unhealthy: Everyone may experience health effects
        return "Unhealthy: Everyone may experience health effects."
    elif aqi == 5:
        # Very Unhealthy: Health alert for everyone
        return "Very Unhealthy: Health alert for everyone."
    else:
        # Hazardous: Health warning of emergency conditions
        return "Hazardous: Health warning of emergency conditions."


def gradio_interface(location):
    """
    Gradio interface function to get air quality data.

    This function is called by Gradio when the user enters a location and
    submits the form. It calls the get_air_quality function to fetch the
    data and returns it to Gradio.

    Args:
        location (str): The location name to be searched.

    Returns:
        dict: A dictionary with the location name, Air Quality Index (AQI)
        and health advisory.
    """
    return get_air_quality(location)


# Set up Gradio interface
interface = gr.Interface(
    fn=gradio_interface,
    inputs="text",
    outputs="json",
    title="Air Quality Monitor",
    description="Enter a location to get the current air quality index (AQI) and health advisory.",
)


# Launch Gradio in the FastAPI app
@app.on_event("startup")
async def startup_event():
    """
    Startup event for the Gradio interface.

    This event is triggered when the FastAPI app starts. It launches the
    Gradio interface on the specified server name and port, and sets the
    share flag to True so that the interface can be accessed from outside
    the container.

    """
    interface.launch(share=True, server_name="0.0.0.0")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
