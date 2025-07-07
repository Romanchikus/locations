from typing import List, Tuple, Union
import folium


def generate_full_map_html(
    locations_data: List[Union[Tuple[float, float], Tuple[float, float, str]]],
) -> str:
    """Generate a full HTML document with an embedded map.

    Args:
        locations_data: List of tuples containing (latitude, longitude) or (latitude, longitude, description)
    """
    # Get first coordinate pair for initial map center
    first_location = locations_data[0] if locations_data else (0, 0)
    m = folium.Map(location=first_location[:2])  # Use only lat/lon for map center

    # Add markers
    for location in locations_data:
        lat, lon = location[:2]  # First two elements are always lat/lon
        description = (
            location[2] if len(location) > 2 else ""
        )  # Get description if provided
        folium.Marker(
            location=(lat, lon),
            popup=description,  # Show description in popup
            # Short description on hover
            tooltip=(
                description[:50] + "..."
                if description and len(description) > 50
                else description
            ),
        ).add_to(m)

    # Draw path between markers
    if len(locations_data) > 1:
        path_coords = [
            (loc[0], loc[1]) for loc in locations_data
        ]  # Extract lat/lon pairs
        folium.PolyLine(path_coords, weight=2, color="red").add_to(m)

    # Fit map bounds to include all markers
    if locations_data:
        first_loc = locations_data[0][:2]  # Get first lat/lon pair
        last_loc = locations_data[-1][:2]  # Get last lat/lon pair
        m.fit_bounds([first_loc, last_loc])

    return m._repr_html_()
