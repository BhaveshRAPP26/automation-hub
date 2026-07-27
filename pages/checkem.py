import re
# note from Tom: I started using the typing module, then realized it would be
# potentially... burdensome. so I commented out. that said, it could be
# useful to implement, as we return many different data types at various points
#from typing import List, Dict, Tuple, Any, Union
import streamlit as st
import pandas as pd
import numpy as np
from rich import print

# begin authentication bits
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

st.set_page_config(page_title="RAPP AE: Check'em", page_icon="✅", layout='wide')


def authentication():
    """
    Wraps streamlit_authenticator functionality, and handles login functionality. 

    Args:
        url_list (list) : A list of URL-like strings.

    Returns:
        tuple: A tuple containing:
               - name: The name associated with the user who is being authenticated.
               - authentication_status: The status of the authentication process. It can contain details 
               about whether the authentication was successful or not.
               - username: The username of the authenticated user.
    """

    with open('auth.yaml') as file:
        config = yaml.load(file, Loader=SafeLoader)

    authenticator = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days'],
        config['preauthorized']
    )

    name, authentication_status, username = authenticator.login('Login', 'main')

    return name, authentication_status, username

name, authentication_status, username = authentication()

def split_url(url: str):
    """
    Splits a URL into a base URL, query string, and hash fragment (if present).

    Args:
        url (str) : Any URL-like string,
                    ex. -
            "https://www.example.com/page/?query_param=query_value#somehashvalue"

    Returns:
        base_url (str) : from ex. above - "https://www.example.com/"
        query_string (str) : from ex. above - "query_param=query_value"
        hash_fragment (str) : from ex. above - "somehashvalue"
        url_errors (list) : from ex. above - "somehashvalue"
    """
    base_url = ""
    query_string = None
    hash_fragment = None
    url_errors = []


    if "#" in url:
        # check for URL fragment before query string start
        if "?" in url and (url.index("#") < url.index("?")):
            url_errors.append('URL fragment ("#") present before query string')
        else:
            url, hash_fragment = url.split("#", 1)


    if "?" in url:
        if url.count("?") > 1:
            url_errors.append(f'There are {url.count("?")} "?" characters in {url}')
            base_url, query_string = url.split("?", 1)
        else:
            base_url, query_string = url.split("?", 1)
    else:
        base_url = url

    if re.search(r"\s+", base_url):
        url_errors.append(f"White space in base URL: {base_url}")

    if not base_url.startswith(('http', 'www', 'https')):
        url_errors.append(f'URL does not start with "http," "https", or "www": {base_url}')

    if "'" in base_url:
        url_errors.append(f"Single quote in base URL: {base_url}")

    return base_url, query_string, hash_fragment, url_errors


def process_query_string(query_string: str):
    """
    Processes a given query string, analyzes it for potential issues, and
    returns the breakdown of the query parameters.

    Args:
        query_string (str) : A string that represents the query part of a URL.
                             For example, "param1=value1&param2=value2".

    Returns:
        warnings (list) : A list of warnings regarding potential issues in the
                          query string, such as absence of a value for a query
                          parameter or presence of duplicate query keys.

        query_params (dict) : A dictionary where each key-value pair represents
                              a query parameter from the URL. Each key is a
                              string that represents the parameter name, and the
                              value is a list of strings representing the corresponding
                              parameter value(s).

        query_errors (list) : A list of errors found in the query string, such as extra
                        "?" characters, presence of whitespace in parameter keys
                        or values, or presence of invalid query parameters.

    """

    query_warnings = []
    query_params = {}
    query_errors = []

    # if there's an extra "?" character besides the open of the query string,
    # append that as an error and immediately return
    if "?" in query_string:
        query_errors.append('Extra "?" in query parameter string')
        return query_warnings, query_params, query_errors

    if not query_string:
        query_errors.append("No query parameters in URL")
        return query_warnings, query_params, query_errors

    query_params_list = query_string.split("&")

    if '' in query_params_list:
        query_warnings.append(\
                f"There are {query_params_list.count('')} repeating '&' characters")

    # we do this to remove any empty elements caused by splitting
    # repeating '&' chars
    query_params_list = [i for i in query_params_list if i != '']

    for param in query_params_list:

        try:

            # if there are more than one "=", add to query_warnings
            if param.count("=") > 1:
                query_warnings.append(f"There are {param.count('=')} '=' in {param}")
            else:
                [ param_key, param_value ] = param.split("=", 1)


            # if no value for a given param, add to query_warnings
                if param_value == '':
                    query_warnings.append(f"No value for key '{param_key}' in URL")

                if param_key in query_params:
                    query_warnings.append(f"Duplicate query parameter key '{param_key}' in URL")

                # if whitespace in param key, add to query_errors
                if " " in param_key:
                    query_errors.append(f"White space in this parameter key: {param_key}")

                # if whitespace in param value, add to query_errors
                if " " in param_value:
                    query_errors.append(f"White space in this parameter value: {param_value}")

                if not is_query_parameter_key_valid(param_key):
                    query_errors.append(f"Invalid query parameter key '{param_key}' in URL")

                if not is_query_parameter_value_valid(param_value):
                    query_errors.append(f"Invalid query parameter value '{param_value}' in URL")

                query_params.setdefault(param_key, []).append(param_value)

        except Exception as e:
            return "An unexpected error has occurred, please try your URLs again later"


    return query_warnings, query_params, query_errors



def is_query_parameter_key_valid(parameter_key: str):
    """
    Evaluates whether a given query parameter key is valid based on specified rules.

    Args:
        parameter_key (str) : A string representing a single query parameter.

    Returns:
        bool: True if the parameter key is valid, i.e., if it only contains
              alphanumeric characters  or one of these symbols:
              (:_-~.).

              The parameter key should not contain the Facebook Dynamic
              Parameters start/end characters ({{ or }}), nor should it contain
              DCM macros, which start with "%" and end with "!".

    Note:
        Validity is based on characters allowed in a URL query parameter as explained here:
        https://stackoverflow.com/questions/1455578/characters-allowed-in-get-parameter
    """

    # regex explained: if any characters in the parameter are NOT a letter,
    # number, % sign, or one of these (:_-~.) - i.e., if they're not a value
    # that should be in a URL query param
    # (for the character set chosen, see:)
    # https://stackoverflow.com/questions/1455578/characters-allowed-in-get-parameter
    return not bool(re.search(r"[^a-zA-Z0-9:_~.-]", parameter_key))

def is_query_parameter_value_valid(parameter_value: str):
    """
    Evaluates whether a given query parameter value is valid based on specified rules.

    Args:
        parameter_value (str) : A string representing a single query parameter value.

    Returns:
        bool: True if the parameter value is valid, i.e., if it only contains
              alphanumeric characters  or one of these symbols:
              (:_-~.).

              The parameter value CAN contain the Facebook Dynamic Parameters
              start/end characters ({{ or }}), and CAN contain DCM macros,
              which start with "%" and end with "!".


    Note:
        Validity is based on characters allowed in a URL query parameter as explained here:
        https://stackoverflow.com/questions/1455578/characters-allowed-in-get-parameter
    """

    # regex explained: if any characters in the parameter are NOT a letter,
    # a number, an otherwise valid URL character - _, ~, ., %, !, -, OR
    #
    if bool(re.search(r"[^a-zA-Z0-9:_~.%!{}-]", parameter_value)):
        return False

    # Check for unbalanced Facebook Dynamic Parameters or DCM macros.
    fb_dynamic_parameter_count = parameter_value.count('{{') == parameter_value.count('}}')
    dcm_macro_count = parameter_value.count('%') == parameter_value.count('!')

    if not fb_dynamic_parameter_count or not dcm_macro_count:
        return False

    # If the string passed both tests, it's valid.
    return True

def is_hash_fragment_valid(fragment: str):
    """
    Evaluates whether a given hash fragment for is valid based on specified rules.

    Args:
        fragment (str) : A string representing a hash fragment.

    Returns:
        bool: True if the fragment is valid, i.e., it only contains alphanumeric characters,
              or one of these symbols: [ %?/:@._~!$&'()*+,;=- ].

    Note:
        The fragment should not contain any character that is not expected to be present in a URL.
    """

    # regex explained: returns True if any characters in the parameter are NOT a letter,
    # number, % sign, or one of these (?/:@._~!$&'()*+,;=-) - i.e., if they're not a value
    # that should be in a hash fragment
    return not bool(re.search(r"[^%a-zA-Z0-9?/:@._~!$&'()*+,;=-]", fragment))


def process_urls(url_list: list):
    """
    Takes a list of URLs, processes each URL, and returns a dictionary of results, unique query parameters,
    warnings, and errors.

    Args:
        url_list (list) : A list of URL-like strings.

    Returns:
        dict: A dictionary containing:
              - "results": a dictionary where the keys are the original URLs and the values are another
                          dictionary containing 'base_url', 'query_params', 'hash_fragment', 'local_errors',
                          and 'local_warnings' for each URL.
              - "unique_query_params": a dictionary where each key-value pair represents a unique query
                                       parameter from all the URLs processed. The key is a string
                                       representing the parameter name, and the value is a list of all unique
                                       values for that parameter across all URLs.
              - "warnings": a list of warnings encountered during processing of all URLs.
              - "errors": a list of errors encountered during processing of all URLs.

    Note:
        A local warning/error refers to a warning/error that occurred while processing a specific URL.
    """

    results = {}
    warnings = []
    errors = []

    # trim leading whitespace (as any ad platforms will trim/invalidate)
    url_list = [i.strip() for i in url_list]

    # get rid of blank lines
    url_list = [i for i in url_list if re.match(r"[^\s]", i)]


    for url in url_list:
        local_warnings = []
        local_errors = []
        unprocessed_url = url
        base_url, query_string, hash_fragment, url_errors = split_url(url)

        if url_errors:
            local_errors.extend(url_errors)
            errors.extend(url_errors)
        if query_string:
            query_warnings, query_params_dict, query_errors = process_query_string(query_string)
            warnings.extend(query_warnings)
            local_warnings.append(query_warnings)
            errors.extend(query_errors)
            local_errors.extend(query_errors)
        else:
            query_params_dict = {}
            warnings.extend([])
            local_warnings.append([])
            if base_url:
                errors.append("No query parameters in URL: is URL missing a \"?\"")
                local_errors.append("No query parameters in URL: is URL missing a \"?\"")

        if hash_fragment and not is_hash_fragment_valid(hash_fragment):
            errors.append(f"Invalid hash fragment in URL: {url}")

        # here we check that base_url and query_params_dict eval to something
        # truthy, because some inputs (e.g., "#N/A") have characters that kind
        # of look like they maybe are URLs (but aren't)
        if base_url and any([query_params_dict, local_errors, local_warnings]):
            results[unprocessed_url] = {
                'base_url': base_url,
                'query_params': query_params_dict,
                'hash_fragment': hash_fragment,
                'local_errors': local_errors,
                'local_warnings': local_warnings,
            }


    # unique_query_params is an aggregate of all unique parameters across all URLs
    unique_query_params = {}
    for url, data in results.items():
        for k, v in data['query_params'].items():
            if k not in unique_query_params:
                unique_query_params[k] = [v]  # v should be a single value as it comes from query_params_dict
            elif v not in unique_query_params[k]:  # only add the value if it's unique
                unique_query_params[k].append(v)

    return {
        "results": results,
        "unique_query_params": unique_query_params,
        "warnings": warnings,
        "errors": errors,
    }


def display_summary(processed_data: dict, test=False):
    """
    Displays a summary of the processed data in a streamlit table. The summary
    includes the total number of URLs processed, the total number of warnings,
    and the total number of errors.

    Args:
        processed_data (dict): A dictionary containing the processed data,
                               including the results, errors, and warnings.

        test (bool, optional): A flag indicating whether the function is being
                               called in a test environment. Defaults to False.

    Returns:
        If `test' is False (default): A streamlit "Summary" table including
                                      total number of URLs, total number of
                                      warnings, and total number of errors.

        If `test` is True:
            summary_data (dict): A dictionary containing the summary table data.

    Displays a summary of the processed data in a table format. The summary
    includes the total number of URLs processed, the total number of warnings,
    and the total number of errors.

    If the `test` argument is set to True, the `summary_data` dict is returned.
    This should only be used as part of the pytest test suite.
    """

    st.subheader("Summary")
    total_urls = len(processed_data['results'])
    total_errors = len(processed_data['errors'])
    total_warnings = len(processed_data['warnings'])

    summary_data = {
        'Total URLs': [total_urls],
        'Total Warnings': [total_warnings],
        'Total Errors': [total_errors]
    }
    # the below outputs a table with "Total URLs processed," etc, as column 1,
    # and the numbers of *things as column 2*. keeping it around in case this
    # format is preferred at some later date
    #summary_data = [['Total URLs processed', total_urls], \
    #        ['Total errors', total_errors], ['Total warnings', total_warnings]]
    #st.table(summary_data)

    # should only be True if being passed in the pytest test suite
    if test:
        # we need to print so pytest's capsys can read the output, and we're
        # ok with this because it turns out it's pretty hard to test a
        # streamlit table in any reasonable sense... so we'll take what we
        # can get
        print(summary_data)


    df_summary_data = pd.DataFrame(summary_data, columns=summary_data.keys())

    # Streamlit table
    styler = df_summary_data.style.hide(axis='index')
    st.write(styler.to_html(), unsafe_allow_html=True)


def display_errors(processed_data: dict, test=False):
    """
    Displays a table of processed URLs and their associated errors.

    Args:
        processed_data (dict): A dictionary containing the processed data,
                               including the results, errors, and warnings.

        test (bool, optional): A flag indicating whether the function is being
                               called in a test environment. Defaults to False.

    Returns:
        If `test' is False (default): A streamlit "Errors" table including
                                      each URL and their associated errors.

        If `test` is True:
            error_data (list): A list containing the table data.

    Displays a table of each URL processed and their associated errors. Only URLs
    with non-empty error fields are included in the table.

    If the `test` argument is set to True, the `error_data` list is returned.
    This should only be used as part of the pytest test suite.
    """

    table_data = []

    for url in processed_data['results']:
        errors = processed_data['results'][url]['local_errors']
        try:
            original_url = url
        except Exception as e:
            errors = ''
        for error in errors:
            table_data.append([original_url, error])

    # make the table
    df_table = pd.DataFrame(table_data, columns=['URL', 'Errors'])
    # filter df to rows/URLs where errors exist
    df_table = df_table[df_table['Errors'] != ""]

    # should only be True if being passed in the pytest test suite
    if test:
        # similarly to above, it's hard to test a table, so let's test the
        # df that we lightly style and turn *into* the table
        return df_table

    # hide the index, because it's kind of ugly
    styler = df_table.style.hide(axis='index')
    # do more magic to make that happen. presto exchango.
    st.write(styler.to_html(), unsafe_allow_html=True)


def display_warnings(processed_data: dict, test=False):
    """
    Display warnings
    """
    table_data = []
    for url in processed_data['results']:
        warnings = processed_data['results'][url]['local_warnings']
        try:
            original_url = url
        except Exception as e:
            warnings = ''
        for warning in warnings[0]:
            table_data.append([original_url, warning])
    df_table = pd.DataFrame(table_data, columns=['URL', 'Warnings'])
    # filter dr to rows/URLs where warnings exist
    df_table = df_table[df_table['Warnings'] != ""]

    # should only be True if being passed in the pytest test suite
    if test:
        # you should sense a trend
        return df_table

    styler = df_table.style.hide(axis='index')
    # do more magic to make that happen
    st.write(styler.to_html(), unsafe_allow_html=True)


def display_processed_urls(processed_data: dict, test=False):
    """ Displays the processed data returned from process_urls function as a streamlit table
    """
    st.subheader("Processed URLs")
    table_data = []

    # Create a list of unique keys in the query_params dictionary
    unique_keys = set()
    for url in processed_data["results"]:
        unique_keys.update(processed_data["results"][url]['query_params'].keys())


    # Add headers for each unique key in the query_params dictionary
    headers = ["Base URL", "Hash Fragment"] + list(sorted(unique_keys))

    # Add a row for each URL in the processed data
    for url in processed_data["results"]:
        row = [ processed_data["results"][url]['base_url'] ]

        query_params = processed_data["results"][url]['query_params']

        # Create a dictionary of query parameter keys and their respective values
        # empty string has been used to join variable 'v' instead of ", " as else,
        # it causes each char in the "Processed URLs" table to be separated by ", "
        params_dict = {k: "".join(v) for k, v in query_params.items()}
        row.append(params_dict)

        hash_fragment = processed_data["results"][url]['hash_fragment']

        row.insert(1, hash_fragment)

        # Add each unique key's value to the row, or an empty string if the key is not present in the query_params dictionary
        for key in sorted(unique_keys):
            row.append(params_dict.get(key, ""))

        # remove the params_dict, since we don't want it in the table
        row.pop(2)
        table_data.append(row)

    # created the df that will later be displayed
    processed_urls_df = pd.DataFrame(table_data, columns=headers)

    # https://www.jitsejan.com/find-and-delete-empty-columns-pandas-dataframe
    # find empty columns
    empty_cols = [col for col in processed_urls_df.columns if processed_urls_df[col].isnull().all()]
    # drop the empty columns
    processed_urls_df.drop(empty_cols, axis=1, inplace=True)

    # finally, replace NaNs with empty strings
    processed_urls_df.replace(np.nan, '', regex=True, inplace=True)
    # set the index for df/table at 1, because probably someone is going to ask for that
    processed_urls_df.index = pd.RangeIndex(start=1, stop=len(processed_urls_df)+1)
    # Display the table
    st.table(processed_urls_df)


def display_unique_param_key_values(processed_data: dict, test=False):
    """
    Displays the unique param keys mapped to a deduped set of values
    as a streamlit table
    """
    st.subheader("Unique Parameter Values")

    # flatten the nested list of lists so pandas won't choke on it
    flattened_query_params_dict = {}
    for k, v in processed_data['unique_query_params'].items():
        flattened_query_params_dict[k] = [query_param_value[0] for query_param_value in v]

    df = pd.DataFrame({k: pd.Series(v) for k, v in flattened_query_params_dict.items()}).replace(np.nan, '', regex=True)

    # set the index for df/table at 1, because probably someone is going to ask for that
    df.index = pd.RangeIndex(start=1, stop=len(df)+1)
    st.table(df)

if authentication_status:
    # hide the top-right menu and footer (that holds the
    # "Made with Streamlit" link)
    hide_streamlit_style = """
                    <style>
                    #MainMenu {visibility: hidden;}
                    footer {visibility: hidden;}
                    </style>
                    """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)
    st.title("Check 'Em")

    st.header("Part 1 - Provide links to be verified")
    urls_input = st.text_area("Paste your URLs here, one URL per line. **Duplicate URLs will be consolidated.**", height=350)

    # Add a button for the user to submit the URLs
    if st.button("Check'em!"):

        processed_urls = process_urls(urls_input.split("\n"))

        display_summary(processed_urls)

        # don't show the Errors table if no errors
        if len(processed_urls['errors']) > 0:
            st.subheader("Errors")
            display_errors(processed_urls)

        # don't show the Warnings table if no errors
        if len(processed_urls['warnings']) > 0:
            st.subheader("Warnings")
            display_warnings(processed_urls)

        display_processed_urls(processed_urls)

        display_unique_param_key_values(processed_urls)
elif authentication_status is False:
    st.error('Username/password is incorrect')
elif authentication_status is None:
    st.warning('Please enter your username and password')
