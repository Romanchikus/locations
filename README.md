# Locations API

A FastAPI application with SQLite database for managing locations.

## Features

- FastAPI web framework
- SQLite database with SQLAlchemy ORM
- Configuration management with Pydantic Settings
- Database migrations with Alembic
- Environment-based configuration

## Setup

1. Install Poetry if you haven't already:
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

2. Install dependencies:
   ```bash
   poetry install
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. Initialize the database:
   ```bash
   poetry run alembic upgrade head
   ```

5. Run the development server:
   ```bash
   poetry run uvicorn app.main:app --reload
   ```

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Key Endpoints

#### Trip Management
- `POST /trip/` - Create a new trip with locations based on the given criteria
  - Accepts trip parameters and generates location suggestions
  - Stores request history for future reference
  - Returns trip details with generated locations

- `POST /trip/exclude` - Modify an existing trip by excluding specific locations
  - Uses `request_id` to reference the original trip
  - Generates new locations based on exclusion criteria
  - Maintains relationship with the parent trip

#### Map Visualization
- `GET /trip/{trip_id}/mapHTML` - Generate an interactive HTML map
  - Displays all locations with tooltips and descriptions
  - Shows the route between locations
  - Provides a full-screen, standalone map view

#### Request History
- `GET /requests/` - List all historical requests
  - Shows all API requests made to the system
  - Can filter to show only requests that resulted in trips
  - Helps track and audit system usage

#### Location Details
- Each location includes:
  - Geographic coordinates (latitude/longitude)
  - Name and description
  - Address details (city, country)
  - Order in the trip sequence

### Example Usage

1. Create a new trip:
```bash
curl -X POST "http://localhost:8000/trip/?trip_type=by_place" \
     -H "Content-Type: application/json" \
     -d '{"preferences": "Historical places in Rome"}'
```

2. Modify trip by excluding locations:
```bash
curl -X POST "http://localhost:8000/trip/exclude?request_id=2" \
     -H "Content-Type: application/json" \
     -d '{"exclude_text": "Skip the Colosseum"}'
```

3. View the trip on an interactive map:
```bash
# Open in browser
http://localhost:8000/trip/2/mapHTML
```

## Development

- Run tests: `poetry run pytest`
- Format code: `poetry run black .`
- Lint code: `poetry run flake8 --exclude .venv --max-line-length=85`
- Type checking: `poetry run mypy .`


### Additional for folium
   ```bash
   sudo apt-get install python3.13-dev build-essential
   ```
