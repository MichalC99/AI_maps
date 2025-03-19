# AI Maps

This application integrates Google Maps with OpenAI via an MCP server.

## Prerequisites
Ensure that the `.env` file is properly configured with both OpenAI and Google Maps API keys.

## Installation
This configuration is compatible with both Poetry and UV.

### Approach 1: UV
#### Installation on Windows:
Run the following command in PowerShell:
```
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
#### Installation on macOS/Linux:
Run the following command in the terminal:
```
curl -LsSf https://astral.sh/uv/install.sh | sh
```

After installing UV, navigate to your project directory and run:
```
uv add "mcp[cli]"
```

### Approach 2: Poetry
#### Installation via pip:
Run the following command:
```
pip install poetry
```
After installing Poetry, navigate to your project directory and run:
```
poetry add mcp[cli]
```

## Starting the Server
To start the server, navigate to the `src/ai_maps` directory and run:
```
python ai_maps_server.py
```

## Testing
### 1. Using Command Line
Open a terminal and run:
```
python ai_maps_client.py
```

### 2. Using Postman
#### Steps:
1. Change the request type to `POST` and use the following URL:
   ```
   http://localhost:8000/ask-for-location
   ```
2. In the **Headers** section, add:
   - **Key**: `Content-Type`
   - **Value**: `application/json`
3. In the **Body** section, select `raw` and use the following JSON format:
   ```json
   {
       "query": "Top museums in Krakow"
   }
   ```

### 3. Using MCP Inspector (testing MCP server; Ensure Node.js is installed)
Run one of the following commands in the terminal:
```
uv run mcp dev ai_maps_server.py
```
or
```
poetry run mcp dev ai_maps_server.py
```
Next, open your browser and navigate to:
```
http://localhost:5173
```
Click the **Connect** button to test the MCP server.
