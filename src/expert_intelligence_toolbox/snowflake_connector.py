"""
This file contains method to interact with Snowflake using Snowpark.
"""
import configparser
from snowflake.sqlalchemy import URL
from sqlalchemy import create_engine
import pandas as pd

def sf_query_to_df(sf_cre_path: str, sf_query: str):
    """
    Load a table from Snowflake into a Pandas DataFrame.

    :param sf_cre_path: Path to Snowflake credentials file.
    :param sf_table_name: Name of the table to load from Snowflake.

    :return: Pandas DataFrame containing the data from Snowflake.
    """
    # Load project configuration
    config = configparser.ConfigParser()
    config.read(sf_cre_path)

    # Snowflake Config
    engine = create_engine(URL(
        account=config['Snowflake']['account'],
        user=config['Snowflake']['user'],
        password=config['Snowflake']['password'],
        database=config['Snowflake']['database'],
        warehouse=config['Snowflake']['warehouse'],
        role=config['Snowflake']['role'],
    ))

    # Execute SQL query to retrieve data from Snowflake
    query = f"{sf_query}"
    df = pd.read_sql_query(query, con=engine)

    # Clean up resources
    engine.dispose()

    return df

import pandas as pd
from sqlalchemy import create_engine

def sf_table_to_df(sf_cre_path: str, sf_schema_name: str, sf_table_name: str, columns_to_select: list = None):
    """
    Load a table from Snowflake into a Pandas DataFrame.

    :param sf_cre_path: Path to Snowflake credentials file.
    :param sf_schema_name: Name of the schema containing the table to load from Snowflake.
    :param sf_table_name: Name of the table to load from Snowflake.
    :param columns_to_select: List of columns to select from the table. If None, all columns are selected.

    :return: Pandas DataFrame containing the data from Snowflake.
    """
    # Load project configuration
    config = configparser.ConfigParser()
    config.read(sf_cre_path)

    # Fill in your Snowflake details here
    engine = create_engine(URL(
        account=config['Snowflake']['account'],
        user=config['Snowflake']['user'],
        password=config['Snowflake']['password'],
        database=config['Snowflake']['database'],
        warehouse=config['Snowflake']['warehouse'],
        role=config['Snowflake']['role']
    ))
    connection = engine.connect()
    # Read the table directly into a DataFrame
    df = pd.read_sql_table(sf_table_name, schema=sf_schema_name, columns=columns_to_select,con=engine )
                                                        
    # Clean up resources
    connection.close()
    engine.dispose()

    return df

def df_to_snowflake(sf_cre_path: str, df_name, sf_schema_name: str, sf_table_name: str, if_exists: str = 'replace'):
    """
    Load a Pandas DataFrame into Snowflake.

    :param sf_cre_path: Path to Snowflake credentials file.
    :param df_name: Name of DataFrame to load into Snowflake. Must be lowercase. 
    :param if_exists: What to do if table already exists in Snowflake.
        replace (default) = Drop and recreate table.
        append = Append data to existing table.

    :return: Table in Snowflake is updated
    """
    # Load project configuration
    config = configparser.ConfigParser()
    config.read(sf_cre_path)
    
    # Create DataFrame
    df = df_name
    
    # Snowflake Config
    engine = create_engine(URL(
        account=config['Snowflake']['account'],
        user=config['Snowflake']['user'],
        password=config['Snowflake']['password'],
        database=config['Snowflake']['database'],
        warehouse=config['Snowflake']['warehouse'],
        role=config['Snowflake']['role'],
    ))
    
    connection = engine.connect()
    
    # table name must be LOWERCASE
    df.to_sql(sf_table_name, schema=sf_schema_name, con=engine, index=False, if_exists=f'{if_exists}', method='multi', chunksize=16000) #make sure index is False, Snowflake doesnt accept indexes
    
    connection.close()
    engine.dispose()
    
    return 'Data uploaded to Snowflake'