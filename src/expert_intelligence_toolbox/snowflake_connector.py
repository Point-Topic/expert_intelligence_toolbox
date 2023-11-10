"""
This file contains methods to interact with Snowflake using SQLAlchemy.
"""
import json
import openai
import pandas as pd
import configparser
from snowflake.sqlalchemy import URL
from sqlalchemy import create_engine
from sqlalchemy import text

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

def sf_connector_df_to_snowflake(cre_path: str, df_name, sf_schema_name: str, sf_table_name: str):
        """
        Load a Pandas DataFrame into Snowflake using Snowflake Connector. 

        :param cre_path: Path to Snowflake and OpenAI credentials file.
        :param if_exists: What to do if table already exists in Snowflake.

        :param metadata: If True, then the function will use OpenAI API to automatically generate metadata for this table (columns and table header).
        :return: Table in Snowflake is updated
        """

        # Load project configuration
        config = configparser.ConfigParser()
        config.read(cre_path)

        # Create DataFrame
        df = df_name
        
        # Snowflake Config
        conn = snow.connect(
            account=config['Snowflake']['account'],
            user=config['Snowflake']['user'],
            password=config['Snowflake']['password'],
            database=config['Snowflake']['database'],
            warehouse=config['Snowflake']['warehouse'],
            role=config['Snowflake']['role'],
            schema=sf_schema_name
        )

        # All columns must be uppercase
        df_name.columns = [x.upper() for x in df_name.columns]
        
        # write to table - table name must be UPPERCASE
        write_pandas(conn, df_name, sf_table_name)

        conn.close()


def sqlalchemy_df_to_snowflake(cre_path: str, df_name, sf_schema_name: str, sf_table_name: str, if_exists: str = 'replace', metadata: bool = False):
    """
    Load a Pandas DataFrame into Snowflake using SQLAlchemy. If metadata = True, then the function will use OpenAI API to automatically generate
    metadata for this table and each column in the table.

    Note: This function uploads chunks of 16,000 rows at a time. This is very slow for large tables. 
    For large tables, use the Snowflake Connector function instead.

    :param cre_path: Path to Snowflake and OpenAI credentials file.
    :param df_name: Name of DataFrame to load into Snowflake. Must be lowercase. 
    :param if_exists: What to do if table already exists in Snowflake.
        replace (default) = Drop and recreate table.
        append = Append data to existing table.
    :param metadata: If True, then the function will use OpenAI API to automatically generate metadata for this table (columns and table header).
    :return: Table in Snowflake is updated
    """
    # Load project configuration
    config = configparser.ConfigParser()
    config.read(cre_path)

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
    

    if metadata == True:    
        messages = [
            {'role': 'system', 'content': 'You are a helpful assistant that converts structured tables into SQL table metadata text which describes table columns and the table in general.'},
            {'role': 'user', 'content': f'I am providing you this data table:{df_name.head(20)}\n\n Please return a JSON object where key = column name, value = your description. The number of items in the dictionary must equal the number of columns in the table plus one. Make the last key-value pair a description for the entire table, where key = "table".'},
            {'role': 'assistant', 'content': f'''
                    One sentence or a few words per column will be an appropriate length for each description. 
                    For some tables, you will need context on our company and what we do (for others, you will not, so use general information!). I am providing this context now:
                    Our company is called Expert Intelligence. We provide broadband datasets and analytics. 
                    Should you see any reference to an 'EKG', this refers to the European Kilometre Grid which we have created, a 1km x 1km grid covering Europe.
                    Should there be any mention of EDGAP, this refers to the European Demographics and Analytics Platform, which is a platform we are building to provide granular (EKG-level) broadband data for all of Europe. 
                    We also frequently make use of NUTS (a European Commission geographic classification system), and use plenty of broadband-related acronyms like FTTP (Fibre-to-the-premises), etc. 
                    You can trust your instinct when creating this metadata, we are not looking for anything very detailed. Just don't make up anything very specific such as units or granularity.
                    If at any point you just see nulls in a column, well, tough luck and you'll probably have to just guess. Do not
                    come back with anything like 'I'm sorry, there are only nulls in this column so I cannot describe the values' - simply do your best even if you are guessing.
                    Your response MUST be in exactly this format (adjust for number of columns):
                    {{
                    "column_1": "Description of column 1",
                    "column_2": "Description of column 2",
                    "table": "Description of entire table"
                    }}
                    A good example of a description would be: {{"Population": "Population in absolute figures, at Local Administrative Unit level, for the year 2020."}}
                    Remember to not forget including a description for the table itself, where key = "table".'''}
        ]
        # print(messages)
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                api_key=config['OpenAI']['key'],
                messages=messages,
                temperature=0,
                request_timeout=150
            )
        except openai.error.APIError as e:
            print(f"OpenAI API returned an API Error: {e}")
            response = f"{e}"
        except openai.error.APIConnectionError as e:
            print(f"Failed to connect to OpenAI API: {e}")
            response = f"{e}"
        except openai.error.RateLimitError as e:
            print(f"OpenAI API request exceeded rate limit: {e}")
            response = f"{e}"

        # Extract the assistant's reply as a dictionary
        assistant_reply = response.choices[0].message["content"]
        try:
            assistant_reply = json.loads(assistant_reply)

        # keeping for debugging
        # print('Type of assistant_reply is: ', type(assistant_reply))
        # print('assistant_reply is: ', assistant_reply)
        # print('The number of columns in the table, plus one, is ',df_name.shape[1]+1)
        # print('Length of dictionary returned by AI (should be same as the above) is ',len(assistant_reply.keys()))
        # If the below fails, we do not want to proceed with updating the metadata
        
        except:
            print("Error - Assistant reply not in JSON/dictionary format. The AI has likely not followed instructions and has not returned a valid JSON/dictionary. Naughty AI.")
            print("Automated metadata generation was not successful. However, data was still uploaded to Snowflake.")
            exit()
        if df_name.shape[1]+1 != len(assistant_reply.keys()):
            print("Warning - Number of columns not equal to number of metadata descriptions produced. Something's wrong here.")
            print("Automated metadata generation was not successful. However, data was still uploaded to Snowflake.")
            exit()

        # Update metadata
        for key, value in assistant_reply.items():
            if key != list(assistant_reply.keys())[-1]:
                # SF syntax is: COMMENT ON COLUMN DATABASE.SCHEMA.TABLE.COLUMN IS 'column_comment';
                metadata_statement = f"comment on column {sf_schema_name}.{sf_table_name}.{key} is '{value}'"
                connection.execute(text(metadata_statement))
            else: # SF syntax is: COMMENT ON TABLE DATABASE.SCHEMA.TABLE IS 'table_comment';
                metadata_statement = f"comment on table {sf_schema_name}.{sf_table_name} is '{value}'"
                connection.execute(text(metadata_statement))

    connection.close()
    engine.dispose()
    
    return 'Data uploaded to Snowflake. If metadata=True, metadata generation was successful.'
