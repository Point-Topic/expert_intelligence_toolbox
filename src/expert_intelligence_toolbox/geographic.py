from OSMPythonTools.overpass import Overpass, overpassQueryBuilder
import pandas as pd
import geolib.geohash
import geopandas as gpd

def convert_text_to_boundary(country: str, location: str, return_geometry: bool = True):
    '''
    This function takes in a country and a city name, and returns the boundary of the city (or the raw boundary coordinates).

    It will not work for areas which are commonly considered to not have a boundary.
    For example, Kentish Town in London is a neighbourhood, and does not have boundaries (think 'city limits').

    The function is able to handle multiple places with identical names in the same country, as it will
    has coordinates into individual polygons based on their geohash.

    Variables:
    country: Country name
    location: Location name
    return_geometry: If True, returns a geopandas dataframe with polygon(s) of locations. If false, returns coordinates of the boundary.
    '''
    overpass = Overpass()

    query = f'''
    area[name="{country}"];
    (
    //try and get the specfic London relation
    relation["type"="boundary"]["name"="{location}"](area);
    );
    (._;>;);
    out body;
    '''

    r = overpass.query(query)

    filtered = [i for i in r.toJSON()['elements'] if 'tags' not in i.keys()]

    coordinates_df = pd.DataFrame(filtered)

    # filter out the points
    coordinates_df = coordinates_df[coordinates_df['type'] == 'node']

    # create a hash by grouping lat and lon
    coordinates_df["geohash"] = coordinates_df.apply(lambda r: geolib.geohash.encode(r["lon"], r["lat"], 3), axis=1)

    # create a geodataframe to store the points
    gdf = gpd.GeoDataFrame(
        coordinates_df, geometry=gpd.points_from_xy(coordinates_df["lon"], coordinates_df["lat"]), crs="epsg:4386"
    )
    # cluster points to polygons as a new geodataframe using convex hull
    polygons = gdf.dissolve(by="geohash", aggfunc={"type": "first", "id":"count"})
    polygons["geometry"] = polygons["geometry"].convex_hull

    # Return a polygon by fault, or coordinates if requested
    if return_geometry == True:
        return polygons
    else:
        return coordinates_df