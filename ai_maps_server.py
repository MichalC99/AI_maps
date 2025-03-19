"""
AI Maps Server
--------------------------------
This script integrates FastMCP with Google Maps and OpenAI API using FastAPI.

To run this example, create a `.env` file with the following values:

OPENAI_API_KEY=...
GOOGLE_MAPS_API_KEY=...
"""

import os
import json
import logging
from typing import List, Optional, Dict, Any

import httpx
from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from openai import OpenAI
from dotenv import load_dotenv

from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ai_maps")

load_dotenv()

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    
    openai_api_key: str
    google_maps_api_key: str

try:
    settings = Settings()
    logger.info("Settings loaded successfully")
    logger.info(f"Google Maps API Key: {settings.google_maps_api_key[:5]}...{settings.google_maps_api_key[-4:]}")
    logger.info(f"OpenAI API Key: {settings.openai_api_key[:5]}...{settings.openai_api_key[-4:]}")
except Exception as e:
    logger.error(f"Error loading settings: {e}")
    logger.error("Please create a .env file with OPENAI_API_KEY and GOOGLE_MAPS_API_KEY")
    settings = None



openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
mcp = FastMCP("AI Maps")
app = FastAPI(title="AI Maps API", description="API for querying location-based information")

class LocationQuery(BaseModel):
    query: str = Field(..., description="Natural language query about a location")

class LocationResponse(BaseModel):
    response: str = Field(..., description="Natural language response with location information")
    locations: List[Dict[str, Any]] = Field(default_factory=list, description="List of locations mentioned in the response")


# FastMCP tools
@mcp.tool()
def search_places(query: str, location: Optional[str] = None, radius: int = 5000) -> List[Dict[str, Any]]:
    """
    Search for places based on a query and optional location.
    
    Args:
        query: The search query (e.g., "restaurants", "parks")
        location: The location to search around (e.g., "Cracow, Poland")
        radius: The search radius in meters (default: 5000)
        
    Returns:
        A list of places matching the query
    """
    logger.info(f"GOOGLE MAPS API CALL: Searching for places with query='{query}', location='{location}', radius={radius}")
    
    lat, lng = None, None
    if location:
        geocode_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={location}&key={settings.google_maps_api_key}"
        logger.info(f"GOOGLE MAPS API CALL: Geocoding location '{location}'")
        with httpx.Client() as client:
            response = client.get(geocode_url)
            response.raise_for_status()
            data = response.json()
            
            if data["status"] == "OK" and data["results"]:
                lat = data["results"][0]["geometry"]["location"]["lat"]
                lng = data["results"][0]["geometry"]["location"]["lng"]
                logger.info(f"GOOGLE MAPS API RESPONSE: Geocoded '{location}' to coordinates ({lat}, {lng})")
            else:
                logger.warning(f"GOOGLE MAPS API RESPONSE: Failed to geocode '{location}'. Status: {data['status']}")
    
    if radius > 50000:
        logger.warning(f"Radius {radius}m exceeds maximum allowed value of 50000m. Capping at 50000m.")
        radius = 50000
    
    places_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "key": settings.google_maps_api_key,
        "radius": radius,
        "type": "establishment"  # This helps with more specific results
    }
    
    if lat and lng:
        params["location"] = f"{lat},{lng}"
    
    if query:
        params["keyword"] = query
    
    logger.info(f"GOOGLE MAPS API CALL: Searching for places with params: {params}")
    with httpx.Client() as client:
        response = client.get(places_url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data["status"] == "OK":
            logger.info(f"GOOGLE MAPS API RESPONSE: Found {len(data['results'])} places within {radius}m radius")
            return data["results"]
        else:
            logger.warning(f"GOOGLE MAPS API RESPONSE: No places found. Status: {data['status']}")
            return []

@mcp.tool()
def get_place_details(place_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a place.
    
    Args:
        place_id: The Google Maps place ID
        
    Returns:
        Detailed information about the place
    """
    logger.info(f"GOOGLE MAPS API CALL: Getting details for place_id='{place_id}'")
    details_url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "key": settings.google_maps_api_key,
        "fields": "name,formatted_address,formatted_phone_number,website,rating,opening_hours,reviews,photos,price_level,geometry"
    }
    
    with httpx.Client() as client:
        response = client.get(details_url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data["status"] == "OK":
            logger.info(f"GOOGLE MAPS API RESPONSE: Successfully got details for place '{place_id}'")
            return data["result"]
        else:
            logger.warning(f"GOOGLE MAPS API RESPONSE: Failed to get place details. Status: {data['status']}")
            return {}

@mcp.tool()
def get_directions(origin: str, destination: str, mode: str = "driving") -> Dict[str, Any]:
    """
    Get directions between two locations.
    
    Args:
        origin: The starting location (address or coordinates)
        destination: The destination location (address or coordinates)
        mode: The transportation mode (driving, walking, bicycling, transit)
        
    Returns:
        Directions information
    """
    logger.info(f"GOOGLE MAPS API CALL: Getting directions from '{origin}' to '{destination}' via {mode}")
    directions_url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": origin,
        "destination": destination,
        "mode": mode,
        "key": settings.google_maps_api_key,
    }
    
    with httpx.Client() as client:
        response = client.get(directions_url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data["status"] == "OK":
            logger.info(f"GOOGLE MAPS API RESPONSE: Successfully got directions")
            return data
        else:
            logger.warning(f"GOOGLE MAPS API RESPONSE: Failed to get directions. Status: {data['status']}")
            return {}

@app.post("/ask-for-location", response_model=LocationResponse)
async def ask_for_location(query: LocationQuery = Body(...)):
    """
    Process a natural language query about locations and return relevant information.
    
    Example query: "What are the top museums in Cracow?"
    """
    logger.info(f"Received query: '{query.query}'")
    
    if not settings:
        logger.error("API keys not configured")
        raise HTTPException(status_code=500, detail="API keys not configured")
    
    try:
        logger.info("OPENAI API CALL: Analyzing query to extract location information")
        
        extraction_prompt = f"""
        Extract location information from this query: "{query.query}"
        
        Please analyze the query and identify:
        1. Any location names mentioned (cities, countries, neighborhoods, etc.)
        2. What type of place the user is looking for (restaurants, museums, parks, etc.)
        3. Any filters or preferences from these categories:
           - Price level: "expensive", "cheap", "moderate", "luxury"
           - Rating: "highly rated", "5-star", "top-rated", "best"
           - Place type: "restaurant", "museum", "park", "hotel", "cafe", "shopping_mall", "tourist_attraction"
           - Open status: "open now", "open late", "24/7"
           - Distance: "within X km/miles", "nearby", "close to"
           - Popularity: "popular", "famous", "touristy", "hidden gem"
           - Language/Region: "Japanese", "Italian", "French", etc.
        
        Return a JSON object with these fields:
        {{
            "location": "The location name, if any, or empty string",
            "place_type": "The type of place the user is looking for, or 'places of interest' if unclear",
            "filters": ["list of specific filters from the categories above"],
            "search_query": "The full original query for fallback"
        }}
        """
        
        extraction_completion = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts structured location information from natural language queries."},
                {"role": "user", "content": extraction_prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        try:
            extracted_info = json.loads(extraction_completion.choices[0].message.content)
            extracted_info = {
                "location": extracted_info.get("location", ""),
                "place_type": extracted_info.get("place_type", "places of interest"),
                "filters": extracted_info.get("filters", []),
                "search_query": query.query  
            }
        except (json.JSONDecodeError, AttributeError, KeyError) as e:
            logger.warning(f"Failed to parse OpenAI JSON response: {e}. Using fallback extraction.")
            extracted_info = {
                "location": "",
                "place_type": "places of interest",
                "filters": [],
                "search_query": query.query
            }
        
        logger.info(f"Extracted information: {extracted_info}")
        
        logger.info(f"Using FastMCP to search for places with query='{extracted_info['search_query']}', location='{extracted_info['location']}'")
        places = search_places(
            query=extracted_info["search_query"],
            location=extracted_info["location"]
        )
        
        detailed_places = []
        for place in places[:3]:  # Get details for top 3 places
            if "place_id" in place:
                logger.info(f"Getting details for place: {place.get('name', 'Unknown')}")
                details = get_place_details(place["place_id"])
                detailed_places.append(details)
        
        places_context = str(detailed_places if detailed_places else places[:5])
        
        logger.info("OPENAI API CALL: Generating natural language response")
        response_prompt = f"""
        Based on the query: "{query.query}"
        
        And the following location data:
        {places_context}
        
        Generate a helpful, natural language response that answers the query.
        Include relevant details like names, addresses, ratings, and any other useful information.
        Format the response in a user-friendly way.
        """
        
        completion = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that provides information about locations."},
                {"role": "user", "content": response_prompt}
            ]
        )
        
        response_text = completion.choices[0].message.content
        logger.info("OPENAI API RESPONSE: Generated natural language response")
        
        return LocationResponse(
            response=response_text,
            locations=detailed_places if detailed_places else places[:5]
        )
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting AI Maps API server...")
    uvicorn.run(app, host="0.0.0.0", port=8000) 