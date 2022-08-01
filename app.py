import configparser
import csv
import json
import requests
import sys
import time

from requests.auth import HTTPBasicAuth


# URL used to obtain tokens from Xero
XERO_TOKEN_URL = "https://identity.xero.com/connect/token"

# Read in the config.ini file
config = configparser.ConfigParser()
config.read('config.ini')
try:
    VOID_TYPE = str(config["DEFAULT"]["VOID_TYPE"])
    DRY_RUN = str(config['DEFAULT']['DRY_RUN'])
except KeyError:
    print("Please check your file is named config.ini - we couldn't find it")
    sys.exit(1)

def check_config():
    """
    Check the config entries are valid
    """
    # Immediately exit if someone hasn't set DRY_RUN properly
    if DRY_RUN not in ("Enabled", "Disabled"):
        print("Dry run needs to be set to Enabled or Disabled. Exiting...")
        sys.exit(1)

    # Check void type is supported, otherwise exit immediately
    if VOID_TYPE not in ("Invoices", "CreditNotes"):
        print("Void type needs to be Invoices or CreditNotes")
        sys.exit(1)


def get_token():
    """
    Obtains a token from Xero, lasts 30 minutes
    """
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {
        'grant_type': "client_credentials",
        'scopes': ['accounting.transactions']
    }
    token_res = post_xero_api_call(XERO_TOKEN_URL, headers, data, auth=True)

    if token_res.status_code == 200:
        print(f"Obtained token, it will expire in 30 minutes")
        return token_res.json()['access_token']
    else:
        print("Couldn't fetch a token, have you set up the App at developer.xero.com?")
        print(f"Status Code: {token_res.status_code}")


def open_csv_file(column_name="InvoiceNumber"):
    """
    Opens a .csv file and prints out invoice IDs
    """
    try:
        with open(config['DEFAULT']['CSV_FILENAME'], newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            return [row[column_name] for row in reader]

    except Exception:
        print("Error: Please check your .csv file is named correctly and contains an InvoiceNumber column")
        raise


def post_xero_api_call(url, headers, data, auth=False):
    """
    Send a post request to Xero
    1) Auth true will pass client id and secret into BasicAuth
    2) Auth false expects you to have added the Bearer token header
    """
    if auth:
        xero_res = requests.post(
            url, 
            headers=headers, 
            auth=HTTPBasicAuth(config['DEFAULT']['CLIENT_ID'], config['DEFAULT']['CLIENT_SECRET']), 
            data=data
        )
    else:
        xero_res = requests.post(
            url, 
            headers=headers, 
            data=json.dumps(data)
        )
    return xero_res


def process_void_job(token, invoice_ids, all_at_once):
    """
    We either void instantly or wait 1 second inbetween API calls using all_at_once
    """
    if not all_at_once:
        for idx in invoice_ids:
            # Sleep 1.5 seconds so it's impossible to hit the rate limit
            # of 60 API calls max per minute
            time.sleep(1.5)
            void_invoice(token, idx)
        return
    
    for idx in invoice_ids:
        void_invoice(token, idx)
    return


def void_invoice(token, invoice_number):
    """
    Voids a given invoice number
    """
    print(f"Asking Xero to void {invoice_number}")

    url = f"https://api.xero.com/api.xro/2.0/{VOID_TYPE}/{invoice_number}"
    headers = {
        'Accept': 'application/json',
        'Authorization': f"Bearer {token}",
        'Content-Type': 'application/json'
    }
    data = {
        "InvoiceNumber": invoice_number,
        "Status": "VOIDED"
    }
    void_res = post_xero_api_call(url, headers, data)

    if void_res.status_code == 200:
        print(f"Voided {invoice_number} successfully!")
    else:
        print(f"Couldn't void {invoice_number}, please check there's no payments applied to it and that it still exists in Xero")
        print(f"Status Code: {void_res.status_code}")
        print(void_res.json())


def main():
    """
    Main execution loop
    """
    try:
        # Request access token from Xero
        print("Asking Xero for an Access Token...")
        token = get_token()

        # Read invoice numbers into program
        # Note: You MUST use a file named invoices.csv
        # The file MUST have a column named InvoiceNumber
        # Refer to README.md for examples
        invoice_ids = set(open_csv_file())

        # Safety mechanism for those wanting to check before committing
        if DRY_RUN == "Enabled":
            print("Dry run is enabled, not voiding anything")
            print(f"Without Dry run we will void: \n{invoice_ids}")
        else:
            if len(invoice_ids) > 60:
                print("Warning: The Xero API limit is 60 calls per minute. We will void one per second.")
                process_void_job(token, invoice_ids, all_at_once=False)
            else:
                print("Warning: The Xero API limit is 60 calls per minute. You are voiding less than 60 so we will blast through them.")
                process_void_job(token, invoice_ids, all_at_once=True)
    except Exception as err:
        print(f"Encountered an error: {str(err)}")


if __name__ == "__main__":
    print("Running bulk void tool...")
    check_config()
    main()
    print("Exiting...")
