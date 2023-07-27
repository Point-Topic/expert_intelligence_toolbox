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


def convert_list_to_boundaries(country: str, locations_list: str, return_geometry: bool = True):
    '''
    This function takes a list of location names and returns the boundary of each location.

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

    # Create dataframe to store results, with index, geohash, geometry columns
    return_polygons_df = pd.DataFrame(columns=['input_location', 'geohash', 'geometry'])
    return_coordinates_df = pd.DataFrame(columns=['input_location', 'type', 'id', 'lat', 'long', 'geohash', 'geometry'])

    overpass = Overpass()

    for location in locations_list:
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

        # add input location
        coordinates_df['input_location'] = location
        polygons['input_location'] = location

        # drop Id and Type columns
        polygons = polygons.drop(columns=["id", "type"]).reset_index()

        # Return a polygon by fault, or coordinates if requested
        if return_geometry == True:
            # concat to dataframe using concat method
            return_polygons_df = pd.concat([return_polygons_df, polygons])
            
        else:
            return_coordinates_df = pd.concat([return_coordinates_df, coordinates_df])
        
    if return_geometry == True:
        return return_polygons_df
    else:
        return return_coordinates_df



def convert_list_to_uk_geog(locations_list: str, lsoa_boundary_files_path: str, lsoa_msoa_la_lookup_path: str, output_geog: str = 'overview'):
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

    # Create DataFrames to hold results with columns 'LSOA21CD', 'LSOA21NM'
    all_results_unique_lsoa_codes_df = pd.DataFrame(columns=['input_location','LSOA21CD', 'LSOA21NM'])
    all_results_unique_msoa_codes_df = pd.DataFrame(columns=['input_location','MSOA21CD', 'MSOA21NM'])
    all_results_unique_la_codes_df = pd.DataFrame(columns=['input_location','LAD22CD', 'LAD22NM'])
    all_results_overview_df = pd.DataFrame(columns=['input_location','LSOA21CD', 'LSOA21NM', 'MSOA21CD', 'MSOA21NM','LAD22CD','LAD22NM'])
    all_results_join_result = pd.DataFrame(columns=['input_location','LSOA21CD', 'LSOA21NM', 'MSOA21CD', 'MSOA21NM', 'LAD22CD', 'LAD22NM', 'index_right', 'geometry','geohash'])

    # Read in the LSOA boundary files
    print('Reading in LSOA boundary file... This will take a while...')
    lsoa_boundary_file = gpd.read_file(lsoa_boundary_files_path)
    # Drop all columns except for LSOA21CD and geometry and reset index and project to epsg:4386 CRS
    lsoa_boundary_file = lsoa_boundary_file[['LSOA21CD', 'geometry']].reset_index(drop=True).to_crs('epsg:4386')
    
    # Read in the LSOA-MSOA-LA lookup table
    # only read in LSOA21CD, LSOA21NM, (LSOA code and name) MSOA21CD, MSOA21NM, (MSOA code and name) LAD22CD, LAD22NM (LA code and name)
    lsoa_msoa_la_lookup = pd.read_csv(lsoa_msoa_la_lookup_path, usecols=['LSOA21CD', 'LSOA21NM', 'MSOA21CD', 'MSOA21NM', 'LAD22CD', 'LAD22NM'])


    for location in locations_list:
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

        try:
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

            # drop Id and Type columns
            polygons = polygons.drop(columns=["id", "type"]).reset_index()

            # Join MSOA and LA to LSOA boundary file
            lsoa_boundary_file_joined = lsoa_boundary_file.merge(lsoa_msoa_la_lookup[['LSOA21CD', 'LSOA21NM', 'MSOA21CD', 'MSOA21NM', 'LAD22CD', 'LAD22NM']], left_on='LSOA21CD', right_on='LSOA21CD', how='left')
            

            print('There are ' + str(num_polygons) + ' polygons in the input location ', location)
            print(polygons)

            # This will return all LSOAs that are within the polygon
            print('Performing spatial join...')
            join_result = gpd.sjoin(lsoa_boundary_file_joined, polygons, how='inner', predicate='intersects')
            # Get list of unique LSOA codes (LSOA21CD) from join_result
            unique_lsoa_codes = join_result[['LSOA21CD', 'LSOA21NM']].drop_duplicates()
            unique_lsoa_codes_df = pd.DataFrame(unique_lsoa_codes, columns=['LSOA21CD', 'LSOA21NM'])
            # Get list of unique MSOA codes (MSOA21CD) from join_result
            unique_msoa_codes = join_result[['MSOA21CD','MSOA21NM']].drop_duplicates()
            unique_msoa_codes_df = pd.DataFrame(unique_msoa_codes, columns=['MSOA21CD', 'MSOA21NM'])
            # Get list of unique LA codes (LAD22CD) from join_result
            unique_la_codes = join_result[['LAD22CD','LAD22NM']].drop_duplicates()
            unique_la_codes_df = pd.DataFrame(unique_la_codes, columns=['LAD22CD', 'LAD22NM'])

            # add input location
            unique_lsoa_codes_df['input_location'] = location
            unique_msoa_codes_df['input_location'] = location
            unique_la_codes_df['input_location'] = location
            join_result['input_location'] = location
            

            if output_geog == 'lsoa':
                all_results_unique_lsoa_codes_df = pd.concat([all_results_unique_lsoa_codes_df, unique_lsoa_codes_df])
            if output_geog == 'msoa':
                all_results_unique_msoa_codes_df = pd.concat([all_results_unique_msoa_codes_df, unique_msoa_codes_df])
            if output_geog == 'la':
                all_results_unique_la_codes_df = pd.concat([all_results_unique_la_codes_df, unique_la_codes_df])
            if output_geog == 'overview':
                # join LSOA, MSOA and LA codes into one dataframe
                overview_df = pd.merge(unique_la_codes_df[['input_location', 'LAD22CD', 'LAD22NM']],
                        unique_msoa_codes_df[['input_location', 'MSOA21CD', 'MSOA21NM']],
                        on='input_location',
                        how='left')
                overview_df = pd.merge(overview_df,
                        unique_lsoa_codes_df[['input_location', 'LSOA21CD', 'LSOA21NM']],
                        on='input_location',
                        how='left')

                all_results_overview_df = pd.concat([all_results_overview_df, overview_df])
            if output_geog == 'raw':
                all_results_join_result = pd.concat([all_results_join_result, join_result])

        except:
            print('Error. Likely no polygons found for ' + location)
            pass

    if output_geog == 'lsoa':
        return all_results_unique_lsoa_codes_df
    elif output_geog == 'msoa':
        return all_results_unique_msoa_codes_df
    elif output_geog == 'la':
        return all_results_unique_la_codes_df
    elif output_geog == 'overview':
        return all_results_overview_df
    elif output_geog == 'raw':
        return all_results_join_result
        

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




def disaggregate_geography_output_pop_is_pop(input_dataframe,key_dataframe, output_pop_column, input_geo, output_geo, metrics):
    """
    This function disaggregates data from one geography to another based on a key table.
    
    'input' refers to the geography that the data is currently reported at, and 'output' refers to the geography that the data will be disaggregated to.
    'output_pop_is_pop' means that populations for e.g. fttp are based on the population of the output geography, not the input geography.
    i.e. input_metric_percent * output_pop = output_metric_pop

    input_geo and output_geo require at least a _id suffix, e.g. 'ekg_id'. the _name suffix is optional, e.g. 'ekg_name' (which does not exist).
    

    :param input_dataframe: Name of dataframe to be disaggregated. It can contain reported_at column, then the disaggregation will be done for each date.
    :param key_dataframe: Name of dataframe with key (lookup) between input and output geography. This table cannot contain a date column.
    :param output_pop_column: Name of column in key_dataframe containing the population of the output geography.
    :param input_geo: Name of input geography. Enter it without suffix, e.g. 'ekg' not 'ekg_id'.
    :param output_geo: Name of output geography. Enter it without suffix, e.g. 'nuts3' not 'nuts3_id'.
    :param metrics: List of metrics to be disaggregated. Enter them without suffix, e.g. 'fttp' not 'fttp_percent'. Enter as list, e.g. ['fttp', 'wimax']

    """
    
    percent_metrics = []
    pop_metrics = []
    for metric in metrics:
        percent_metrics = percent_metrics + [metric + '_percent']
        pop_metrics = pop_metrics + [metric + '_pop']

    input_geo_id = input_geo + '_id'
    input_geo_name = input_geo + '_name'
    output_geo_id = output_geo + '_id'
    output_geo_name = output_geo + '_name'

    # drop input geometry column if exists
    if 'geometry' in input_dataframe.columns:
        input_dataframe = input_dataframe.drop(columns=['geometry'])

    # drop input_geo_name column if exists in both tables to avoid duplicate columns
    if input_geo_name in input_dataframe.columns and input_geo_name in key_dataframe.columns:
        input_dataframe = input_dataframe.drop(columns=[input_geo_name])
    
    # drop columns in key_dataframe not in [input_geo_id, input_geo_name, output_geo_id, output_geo_name, output_pop_column, 'geometry'] if they exist
    for column in key_dataframe.columns:
        if column not in [input_geo_id, input_geo_name, output_geo_id, output_geo_name, output_pop_column, 'geometry']:
            key_dataframe = key_dataframe.drop(columns=[column])

    # join
    output_dataframe = pd.merge(key_dataframe,input_dataframe, on=input_geo_id, how='left')

    # calculate pop metrics
    for metric in metrics:
        output_dataframe[metric + '_pop'] = output_dataframe[metric + '_percent'] * output_dataframe[output_pop_column]
    
    return output_dataframe


def disagg_geog_to_ekg_mixed_geog_releases_pop(input_dataframe, key_dataframe, nuts_releases_lookup, input_geo, output_geo, input_pop_column, output_pop_weight_column): # , output_directory
    """
    This function disaggregates population data from NUTS3 to EKG level. 
    It takes as input a dataframe containing population data at NUTS3 level, a dataframe containing the EKG-NUTS3 lookup, a dataframe containing the NUTS release years, and a list of metrics to disaggregate. 
    It returns a dataframe containing the disaggregated population data at EKG level. 
    
    :param input_dataframe: Name of dataframe with the population to be disaggregated. In long format.
    :param key_dataframe: Name of dataframe with key (lookup) between input and output geography. This table cannot contain a date column.
    :param nuts_releases_lookup: Lookup table between country-reporting year-NUTS release year. Column 'match' is either 'yes' or 'no' depending on whether there is a match.
    :param input_geo: Name of input geography. Enter it without suffix, e.g. 'nuts3' not 'nuts3_id'. For now, only tested with NUTS3.
    :param output_geo: Name of output geography. Enter it without suffix, e.g. 'ekg' not 'ekg_id'. For now, only tested with EKG.
    :param input_pop_column: Name of column in input_dataframe containing the population of the input geography.
    :param output_pop_weight_column: Name of column in key_dataframe containing the population of the output geography which will be used as a weight.

    """

    input_geo_id = input_geo + '_id'
    input_geo_name = input_geo + '_name'
    output_geo_id = output_geo + '_id'
    output_geo_name = output_geo + '_name'
    all_results_df = pd.DataFrame()
    for year in input_dataframe['reported_at'].unique():
        input_dataframe_year = input_dataframe[input_dataframe['reported_at'] == year]
        for country in input_dataframe[input_geo_id].str[:2].unique():
            try: 
                matching_nuts_version = nuts_releases_lookup[(nuts_releases_lookup['country_code'] == country) & (nuts_releases_lookup['reported_at'] == year) & (nuts_releases_lookup['match'] == 'yes')]['release_year'].values[0]
                
                print('Now disaggregating population data for year ',year,' and country ',country,' using NUTS version ',matching_nuts_version,'.')
                
                input_dataframe_country = input_dataframe_year[(input_dataframe_year[f'{input_geo_id}'].str[:2] == country)]
                key_dataframe_country = key_dataframe[(key_dataframe[f'{input_geo_id}_{matching_nuts_version}'].str[:2] == country)]
                # we drop columns again because we still have all 5 releases in here. we want only the chosen one now. 
                for column in key_dataframe_country.columns:             
                        if column not in [f'{output_geo_id}', f'{output_pop_weight_column}', f'{input_geo_id}_{matching_nuts_version}', 'country_code', 'geometry']: 
                                key_dataframe_country = key_dataframe_country.drop(columns=[column])
                key_dataframe_country = key_dataframe_country.rename(columns = {f'{input_geo_id}_{matching_nuts_version}': f'{input_geo_id}'})
                
                # for each EKG, add a weight which is equal to pop_weight as proportion of sum(prop_weight) for entire NUTS3
                # weight, as a proportion of 1, is the proportion of output_pop_weight_column as a proportion of that NUTS3, for the relevant NUTS release version. 
                
                key_dataframe_country['weight'] = key_dataframe_country[f'{output_pop_weight_column}'] / key_dataframe_country.groupby([f'{input_geo_id}'])[f'{output_pop_weight_column}'].transform('sum')
                
                output_dataframe = pd.merge(key_dataframe_country,input_dataframe_country,how='left',left_on=[f'{input_geo_id}'],right_on=[input_geo_id])

                output_dataframe[f'{output_geo}_pop'] = round(output_dataframe[f'{input_pop_column}'] * output_dataframe['weight'],4)
                
                output_dataframe.drop(columns=['weight',f'{input_pop_column}',f'{input_geo_id}'],inplace=True) # because these are at NUTS3 level, not EKG level.
                all_results_df = pd.concat([all_results_df, output_dataframe])
                
            except:
                print('Warning! No matching NUTS version for country ',country,' and year ',year)

    return all_results_df


def disagg_geog_to_ekg_mixed_geog_releases_percent(input_dataframe, key_dataframe,nuts_releases_lookup, output_pop_column, input_geo, output_geo, metrics, output_directory):
    """
    This function disaggregates percentage metrics from an input geography down to EKG level, using a key dataframe. The key dataframe MUST have a country_code column.
    No populations will be calculated as part of this process, and the output_pop_column is only retained to be passed to the output dataframe but not used in calculations. 
    The output_directory must be a DIRECTORY, not a filename.

    :param input_dataframe: The input dataframe to disaggregate. Must have a country_code column.
    :param key_dataframe: The key dataframe to use for disaggregation. Cannot have a reported_at/date column.
    :param nuts_releases_lookup: The lookup table to use to match country_code and reported_at to a NUTS release year.
    :param output_pop_column: The name of the column in the input_dataframe that contains the population of the input geography. 
    This will be passed to the output dataframe but not used in calculations.
    :param input_geo: The name of the input geography. Must be passed without siffixes. e.g. 'nuts', not 'nuts_id'.
    :param output_geo: The name of the output geography. Must be passed without siffixes. e.g. 'ekg', not 'ekg_id'.
    :param metrics: A list of metrics to disaggregate. Must be passed without suffixes. e.g. 'overall_fixed_broadband_coverage', not 'overall_fixed_broadband_coverage_percent'.
    :param output_directory: The directory to save the output disaggregated dataframes to. Must be a directory, not a filename. e.g.: 'bin/ebm/historic/02_transform/'
    """
    warnings = 0
    all_years = input_dataframe['reported_at'].unique()
    
    input_geo_id = input_geo + '_id'
    input_geo_name = input_geo + '_name'
    output_geo_id = output_geo + '_id'
    output_geo_name = output_geo + '_name'
    
    country_names = input_dataframe[input_geo_id].str[:2].unique()
    percent_metrics = []
    pop_metrics = []
    for metric in metrics:
            percent_metrics = percent_metrics + [metric + '_percent']
            pop_metrics = pop_metrics + [metric + '_pop']

    for country in country_names:
            all_results_df = pd.DataFrame()
            for year in all_years:
                    try:
                            matching_nuts_version = nuts_releases_lookup[(nuts_releases_lookup['country_code'] == country) & (nuts_releases_lookup['reported_at'] == year) & (nuts_releases_lookup['match'] == 'yes')]['release_year'].values[0]
                            print('Disaggregating country ',country,'for year ',year,'. First matching NUTS version found is ', matching_nuts_version)

                            #input and key dataframe filtered by country (and year for input)
                            input_dataframe_country = input_dataframe[(input_dataframe['country_code'] == country) & (input_dataframe['reported_at'] == year)]

                            key_dataframe_country = key_dataframe[(key_dataframe[f'{input_geo_id}_{matching_nuts_version}'].str[:2] == country)]
                            
                            # we drop columns again because we still have all 5 releases in here. we want only the chosen one now. 
                            for column in key_dataframe_country.columns:
                                    if column not in [f'{output_geo_id}',output_pop_column, f'{input_geo_id}_{matching_nuts_version}', 'geometry']: 
                                            key_dataframe_country = key_dataframe_country.drop(columns=[column])
                            key_dataframe_country = key_dataframe_country.rename(columns = {f'{input_geo_id}_{matching_nuts_version}': f'{input_geo_id}'})
                            
                            input_dataframe_country = input_dataframe_country[input_dataframe_country[f'{input_geo_id}'].str.len() == 5]

                            output_dataframe = pd.merge(key_dataframe_country, input_dataframe_country, on=f'{input_geo_id}', how='left')
                            
                            for column in output_dataframe.columns: # because these are at NUTS3 level, not EKG level.
                                    if column in [f'{input_geo_id}',f'{input_geo_name}']:
                                            output_dataframe = output_dataframe.drop(columns=[column])
                            
                            # COMMENTING OUT FOR NOW
                            # for metric in metrics:
                            #         output_dataframe[metric + '_pop'] = output_dataframe[metric + '_percent'] * output_dataframe[output_pop_column]

                            all_results_df = pd.concat([all_results_df, output_dataframe])
                    except:
                            print('Warning! No matching NUTS version for ', country, 'in year ', year)
                            warnings +=1
                            pass
            

            all_results_df.to_csv(f'{output_directory}/disagg_output_{country}.csv',index=False)
    if warnings != 0:
            print('Attention: There were ',warnings,' warnings during this run.')