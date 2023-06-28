"""
This file contains method to interact with Snowflake using Snowpark
"""
from snowflake.snowpark.session import Session
from snowflake.snowpark.functions import col
import configparser
from snowflake.sqlalchemy import URL
from sqlalchemy import create_engine

def load_table(sf_cre_path: str, columns: list, table: str):
    """
    Load columns in table and return a pandas dataframe.

    :param sf_cre_path: path to Snowflake credentials config file
    :param columns: list of columns need to be fetched
    :param table: name of table in Snowflake

        returns:
            df: Pandas dataframe
    """
    # Validate config path
    if sf_cre_path.split(".")[-1] not in ["cfg", "config"]:
        raise Exception("The path must be in .cfg or .config format.")

    # Load project configuration
    config = configparser.ConfigParser()
    config.read(sf_cre_path)

    # Connecting to Snowflake
    snowflake_conn_prop = {
        "account": config['Snowflake']['account'],
        "user": config['Snowflake']['user'],
        "password": config['Snowflake']['password'],
        "role": config['Snowflake']['role'],
        "database": config['Snowflake']['database'],
        "schema": config['Snowflake']['schema'],
        "warehouse": config['Snowflake']['warehouse'],
    }
    session = Session.builder.configs(snowflake_conn_prop).create()
    # Load data into Pandas dataframe
    data_obj = session.table(table).select(
            *[col(column) for column in columns]
        )
    df = data_obj.toPandas()

    return df
    

def load_query(sf_cre_path: str, query: str):
    """
    Returns result of Snowflake query as a Pandas dataframe.

    :param sf_cre_path: path to Snowflake credentials config file
    :param query: query that need to be ran

        returns:
            df: Pandas dataframe
    """
    # Validate config path
    if sf_cre_path.split(".")[-1] not in ["cfg", "config"]:
        raise Exception("The path must be in .cfg or .config format.")

    # Load project configuration
    config = configparser.ConfigParser()
    config.read(sf_cre_path)

    # Connecting to Snowflake
    snowflake_conn_prop = {
        "account": config['Snowflake']['account'],
        "user": config['Snowflake']['user'],
        "password": config['Snowflake']['password'],
        "role": config['Snowflake']['role'],
        "database": config['Snowflake']['database'],
        "schema": config['Snowflake']['schema'],
        "warehouse": config['Snowflake']['warehouse'],
    }
    session = Session.builder.configs(snowflake_conn_prop).create()
    # Load data into Pandas dataframe
    data_obj = session.sql(query)
    df = data_obj.toPandas()

    return df


def df_to_snowflake(sf_cre_path: str, df_name, sf_table_name: str, if_exists: str = 'replace'):
    """
    Load a Pandas DataFrame into Snowflake.

    :param sf_cre_path: Path to Snowflake credentials file.
    :param df_name: Name of DataFrame to load into Snowflake. Must be lowercase. 
    :param if_exists: What to do if table already exists in Snowflake.
        replace (default) = Drop and recreate table.
        append = Append data to existing table.

    """
    # Load project configuration
    config = configparser.ConfigParser()
    config.read(sf_cre_path)
    
    # Create DataFrame
    df = df_name
    
    # Fill in your SFlake details here
    engine = create_engine(URL(
        account=config['Snowflake']['account'],
        user=config['Snowflake']['user'],
        password=config['Snowflake']['password'],
        database=config['Snowflake']['database'],
        schema=config['Snowflake']['schema'],
        warehouse=config['Snowflake']['warehouse'],
        role=config['Snowflake']['role'],
    ))
    
    connection = engine.connect()
    
    # table name must be LOWERCASE
    df.to_sql(sf_table_name, con=engine, index=False, if_exists='replace') #make sure index is False, Snowflake doesnt accept indexes
    
    connection.close()
    engine.dispose()
    
    return 'Data uploaded to Snowflake'