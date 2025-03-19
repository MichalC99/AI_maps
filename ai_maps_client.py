"""
AI Maps Client
--------------------------------
This script allows to communicate with the AI Maps service via command line.
"""


import json
import sys
from typing import Dict, Any

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

API_URL = "http://localhost:8000"
console = Console()

def ask_for_location(query: str) -> Dict[str, Any]:
    """
    Send a natural language query to the AI Maps API.
    
    Args:
        query: Natural language query about a location
        
    Returns:
        API response with location information
    """
    try:
        with httpx.Client() as client:
            response = client.post(
                f"{API_URL}/ask-for-location",
                json={"query": query},
                timeout=30.0  # Longer timeout for LLM processing
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        console.print(f"[bold red]Error:[/bold red] HTTP Status Error {e.response.status_code}")
        if e.response.headers.get("content-type") == "application/json":
            console.print(e.response.json())
        return {"error": str(e)}
    except httpx.RequestError as e:
        console.print(f"[bold red]Error:[/bold red] Request Error - {str(e)}")
        return {"error": str(e)}
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        return {"error": str(e)}

def display_location_response(response: Dict[str, Any]) -> None:
    """
    Display the location response in a nice format.
    
    Args:
        response: API response with location information
    """
    if "error" in response:
        console.print(Panel(f"[bold red]Error:[/bold red] {response['error']}", 
                           title="AI Maps Error", 
                           border_style="red"))
        return
    
    console.print(Panel(Markdown(response["response"]), 
                       title="AI Maps Response", 
                       border_style="green"))
    
    if response.get("locations"):
        console.print("\n[bold blue]Location Details:[/bold blue]")
        for i, location in enumerate(response["locations"], 1):
            name = location.get("name", "Unknown")
            address = location.get("formatted_address", location.get("vicinity", "Unknown address"))
            rating = location.get("rating", "No rating")
            
            console.print(Panel(
                f"[bold]{name}[/bold]\n"
                f"Address: {address}\n"
                f"Rating: {rating} ⭐\n",
                title=f"Location {i}",
                border_style="blue"
            ))

def main():
    console.print(Panel("[bold]AI Maps Client[/bold]\n"
                       "Ask questions about locations in natural language.",
                       title="Welcome",
                       border_style="yellow"))
    
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = console.input("[bold yellow]Enter your location query:[/bold yellow] ")
    
    console.print(f"\n[bold]Processing query:[/bold] {query}\n")
    
    response = ask_for_location(query)    
    display_location_response(response)

if __name__ == "__main__":
    main() 