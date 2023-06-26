from OSMPythonTools.overpass import Overpass, overpassQueryBuilder
from geopy.geocoders import Nominatim
from shapely.geometry import Point
import geolib.geohash
import geopandas as gpd
import pandas as pd
import time
import csv


def convert_string_to_boundary(country: str, location: str, return_geometry: bool = True):
    '''
    This function takes in a country and a city name, and returns the boundary of the city (or the raw boundary coordinates).

    It will not work for areas which are commonly considered to not have a boundary.
    For example, Kentish Town in London is a neighbourhood, and does not have boundaries (think 'city limits').

    The function is able to handle multiple places with identical names in the same country, as it will
    has coordinates into individual polygons based on their geohash.

    Variables:
    country: Country name
    location: Location name
    return_geometry (default = True): 
        If True, returns a geopandas dataframe with polygon(s) of locations. 
        If false, returns coordinates of the boundary.
        
    '''
    overpass = Overpass()

    query = f'''
    area[name="{country}"];
    (
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
    

def convert_string_to_uk_geog(location: str, lsoa_boundary_files_path: str, lsoa_msoa_la_lookup_path: str, output_geog: str = 'overview'):
    '''
    This function converts a location to a list of LSOAs, MSOAs, or LAs.
    This current version only works for England and Wales (LSOAs), and not Scotland or Northern Ireland.

    It is an extended verison of the function convert_string_to_boundary and comes with the same caveats.

    However, it will then peform a spatial join between the polygon matching the location input and the LSOA boundary files 
    to find all LSOAs that are within the boundary of the location.

    From there, a lookup table is used to return the desired output geographies (LSOA, MSOA, or LA).

    For this to work, you must download and save locally these two files:
    lsoa_boundary_files_path (as GEOJSON): https://geoportal.statistics.gov.uk/datasets/ons::lsoa-dec-2021-boundaries-full-clipped-ew-bfc/explore
    lsoa_msoa_la_lookup_path (as CSV): https://geoportal.statistics.gov.uk/datasets/ons::oas-to-lsoas-to-msoas-to-lep-to-lad-december-2022-lookup-in-england-v2/explore

    Variables:
    location: Location name, e.g. 'London'
    lsoa_boundary_files_path: Path to the LSOA boundary files
    lsoa_msoa_la_lookup_path: Path to the lookup table
    output_geog (default = 'overview'): The output geography. Options are:
        'lsoa': returns LSOA code and name 
        'msoa': returns MSOA code and name
        'la': returns LA code and name
        'overview': returns all three pairs
        'raw':  returns the raw join results including geometry column
    '''

    overpass = Overpass()

    query = f'''
    area[name="United Kingdom"];
    (
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

    # Count the number of polygons in polygons
    num_polygons = len(polygons)

    # Read in the LSOA boundary files
    print('Reading in LSOA boundary file... This will take a while...')
    lsoa_boundary_file = gpd.read_file(lsoa_boundary_files_path)
    # Drop all columns except for LSOA21CD and geometry and reset index
    lsoa_boundary_file = lsoa_boundary_file[['LSOA21CD', 'geometry']].reset_index(drop=True)
    
    # Read in the LSOA-MSOA-LA lookup table
    # only read in LSOA21CD, LSOA21NM, (LSOA code and name) MSOA21CD, MSOA21NM, (MSOA code and name) LAD22CD, LAD22NM (LA code and name)
    lsoa_msoa_la_lookup = pd.read_csv(lsoa_msoa_la_lookup_path, usecols=['LSOA21CD', 'LSOA21NM', 'MSOA21CD', 'MSOA21NM', 'LAD22CD', 'LAD22NM'])

    # Join MSOA and LA to LSOA boundary file
    lsoa_boundary_file = lsoa_boundary_file.merge(lsoa_msoa_la_lookup[['LSOA21CD', 'LSOA21NM', 'MSOA21CD', 'MSOA21NM', 'LAD22CD', 'LAD22NM']], left_on='LSOA21CD', right_on='LSOA21CD', how='left')
    

    print('There are ' + str(num_polygons) + ' polygons in the input location.')
    print(polygons)
    
    # Project lsoa_boundary_file to epsg:4386 CRS
    lsoa_boundary_file = lsoa_boundary_file.to_crs('epsg:4386')

    # This will return all LSOAs that are within the polygon
    print('Performing spatial join...')
    join_result = gpd.sjoin(lsoa_boundary_file, polygons, how='inner', predicate='intersects')
    
    # Get list of unique LSOA codes (LSOA21CD) from join_result
    unique_lsoa_codes = join_result[['LSOA21CD', 'LSOA21NM']].drop_duplicates()
    unique_lsoa_codes_df = pd.DataFrame(unique_lsoa_codes, columns=['LSOA21CD', 'LSOA21NM'])
    # Get list of unique MSOA codes (MSOA21CD) from join_result
    unique_msoa_codes = join_result[['MSOA21CD','MSOA21NM']].drop_duplicates()
    unique_msoa_codes_df = pd.DataFrame(unique_msoa_codes, columns=['MSOA21CD', 'MSOA21NM'])
    # Get list of unique LA codes (LAD22CD) from join_result
    unique_la_codes = join_result[['LAD22CD','LAD22NM']].drop_duplicates()
    unique_la_codes_df = pd.DataFrame(unique_la_codes, columns=['LAD22CD', 'LAD22NM'])

    if output_geog == 'lsoa':
        return unique_lsoa_codes_df
    elif output_geog == 'msoa':
        return unique_msoa_codes_df
    elif output_geog == 'la':
        return unique_la_codes_df
    elif output_geog == 'overview':
        output_df = pd.DataFrame({'LSOA21CD': unique_lsoa_codes, 'MSOA21CD': unique_msoa_codes, 'LAD22CD': unique_la_codes})
    elif output_geog == 'raw':
        return join_result
    


def convert_string_to_coordinates(path_to_input_csv:str, path_to_output_csv:str, append_str_to_input: str = ''):
    '''
    Converts a string to point location by finding closest OSM address, using Nominatim service of OSM. 
    Returns output geographies(lat/long, wkt) and returns an exact address if one was matched on OSM.

    Will (try to) handle any input, just like Google Maps will try finding anything you type into its search bar.
    
    Input CSV must be in this format (one column, LOCATIONS as header, any row containing a comma wrapped in " "):
    LOCATIONS
    London
    Southampton
    "North Hill, London"

    Variables:
    path_to_input_csv: path to input file in CSV format. Use format above. 
    path_to_output_csv: path to output file in CSV format. Will create file if not exists. 
    append_str_to_input (Default = ''): set to ',United Kingdom' you want to check 
    'London, United Kingdom'; 'Southampton, United Kingdom' for all inputs.
    '''

    # Validate input path
    if path_to_input_csv.split(".")[-1] not in ["csv"]:
        raise Exception("The path must be in .csv or format.")
    
    # Communicates with OpenStreetMap Nomatim service
    geolocator = Nominatim(user_agent="test1")
    #Read in the address file
    locations = pd.read_csv(path_to_input_csv)

    for i in range(len(locations)):
        
        location = locations.iloc[i].to_string(index=False)
        location = f'{location}, {append_str_to_input}'

        try:
            location = geolocator.geocode(location)

            wkt = Point(location.longitude, location.latitude)
            
            output_addresses = pd.DataFrame(
                {
                    'location_name': [locations.iloc[i].to_string(index=False)],
                    'long': [location.latitude],
                    'lat': [location.latitude],
                    'wkt': [wkt],
                    'address_exact': [location.address]
                }
            )
        except Exception as e:
            output_addresses = pd.DataFrame({
                    'location_name': [locations.iloc[i].to_string(index=False)],
                    'long': '',
                    'lat': '',
                    'wkt': '',
                    'address_exact': str(e)
            })
        
        print(output_addresses) if i == 0 else print(output_addresses.values)
        
        # Save addresses to output file
        output_addresses.to_csv(path_to_output_csv, 
                                mode='w+' if i == 0 else 'a', 
                                header=True if i == 0 else False, index=False)    
        time.sleep(1) # to make sure nominatim doesnt block due to too many requests

    print('Program has finished running')


def convert_coordinates_to_address(path_to_input_csv: str, path_to_output_csv: str):
    '''
    Converts lat/long coordinates to address using Nominatim service of OSM.

    Inputs must be a CSV with the following format:
    location,lat,long
    Place A,40.712776,-74.005974
    Place B,51.5074,-0.1278
    Place C,48.8566,2.3522

    Variables:
    path_to_input_csv: path to input file in CSV format. Use format above.
    path_to_output_csv: path to output file in CSV format. Will create file if not exists.
    '''

    if path_to_input_csv.split(".")[-1] not in ["csv"]:
        raise Exception("The path must be in .csv or format.")
    
    # Create Nominatim geocoder instance
    geolocator = Nominatim(user_agent="coordinate_converter")

    # Open input and output files
    with open(path_to_input_csv, 'r') as input_csv, open(path_to_output_csv, 'w', newline='') as output_csv:
        reader = csv.DictReader(input_csv)
        fieldnames = ['location', 'lat', 'long', 'output_address']
        writer = csv.DictWriter(output_csv, fieldnames=fieldnames)
        writer.writeheader()

        # Process each row in the input CSV
        for row in reader:
            location = row['location']
            lat = row['lat']
            lon = row['long']

            # Convert coordinates to address
            coordinates = f"{lat}, {lon}"
            try:
                address = geolocator.reverse(coordinates)
            except Exception as e:
                address = str(e)

            # Write the result to the output CSV
            writer.writerow({
                'location': location,
                'lat': lat,
                'long': lon,
                'output_address': str(address)
            })

    print("Conversion complete.")