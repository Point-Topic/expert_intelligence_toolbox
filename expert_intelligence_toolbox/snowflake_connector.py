"""
This file contains method to interact with Snowflake using Snowpark
"""
from snowflake.snowpark.session import Session
from snowflake.snowpark.functions import col
import configparser

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
