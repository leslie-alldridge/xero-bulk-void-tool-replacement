import requests
from app import post_xero_api_call, get_token, process_void_job


# URL used to obtain tokens from Xero
XERO_TOKEN_URL = "https://identity.xero.com/connect/token"
CONTACT_ID = "f1d403d1-7d30-46c2-a2be-fc2bb29bd295"


def create_invoices(quantity, debug=False):
    """
    Create dummy invoices under 24 Locks
    """
    token = get_token()

    url = f"https://api.xero.com/api.xro/2.0/Invoices"
    headers = {
        'Accept': 'application/json',
        'Authorization': f"Bearer {token}",
        'Content-Type': 'application/json'
    }
    data = {
        "Type": "ACCREC",
        "Contact": {
            "ContactID": CONTACT_ID
        },
        "DueDate": "2020-01-01 17:15:35",
        "LineItems": [
            {
            "Description": "Services as agreed",
            "Quantity": "4",
            "UnitAmount": "100.00",
            "AccountCode": "200"
            }
        ],
        "Status": "AUTHORISED"
    }

    for num in range(quantity):
        print(f"Creating invoice: {num}")
        res = post_xero_api_call(url, headers, data, auth=False)
        if debug:
            print(res.json())


def void_invoices(debug, token):
    """
    Voids invoices created under 24 Locks
    """
    base_url = f"https://api.xero.com/api.xro/2.0/Invoices"
    headers = {
        'Accept': 'application/json',
        'Authorization': f"Bearer {token}",
        'Content-Type': 'application/json'
    }
    query = f'?Statuses=AUTHORISED&ContactIDs={CONTACT_ID}'
    final_url = f"{base_url}{query}"
    
    print(f"Getting invoices...{final_url}")
    response = requests.get(final_url, headers=headers)
    data = response.json()

    if debug:
        print(data)
    
    if data["Status"] == 'OK':
        invoice_ids = [invoice["InvoiceID"] for invoice in data["Invoices"]]
        process_void_job(token, invoice_ids, False)
    else:
        print("Error: Non OK Status Code")


def main(debug):
    """
    Creates 
    """
    num = int(input("How many invoices should we create?"))
    create_invoices(num, debug)

    should_void = str(input("Do you want to void them? y/n"))
    if should_void in ("y", "yes"):
        token = get_token()
        void_invoices(debug, token)
        return
    return


if __name__ == "__main__":
    print("Running data generator...")
    # Debug mode prints json responses from Xero when enabled
    debug = False
    main(debug)
