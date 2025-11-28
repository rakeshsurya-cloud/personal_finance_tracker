import os
import datetime
import plaid
from plaid.api import plaid_api
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.transactions_sync_request import TransactionsSyncRequest
from plaid.model.transactions_sync_request_options import TransactionsSyncRequestOptions
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions
from plaid.model.products import Products
from plaid.model.country_code import CountryCode
from dotenv import load_dotenv

load_dotenv()

# --- Plaid Client Setup ---
PLAID_CLIENT_ID = os.getenv('PLAID_CLIENT_ID')
PLAID_SECRET = os.getenv('PLAID_SECRET')
PLAID_ENV = os.getenv('PLAID_ENV', 'sandbox')

host = plaid.Environment.Sandbox
if PLAID_ENV == 'development':
    host = plaid.Environment.Development
elif PLAID_ENV == 'production':
    host = plaid.Environment.Production


if not PLAID_CLIENT_ID or not PLAID_SECRET:
    # Return dummy client or handle error gracefully in functions
    client = None
else:
    configuration = plaid.Configuration(
        host=host,
        api_key={
            'clientId': PLAID_CLIENT_ID,
            'secret': PLAID_SECRET,
        }
    )
    api_client = plaid.ApiClient(configuration)
    client = plaid_api.PlaidApi(api_client)

def create_link_token(user_id: str):
    """
    Generates a Link Token to initialize Plaid Link on the client side.
    """
    if not client:
        raise ValueError("Plaid credentials not set in .env")
        
    request = LinkTokenCreateRequest(
        products=[Products('transactions')],
        client_name="Personal Finance Tracker",
        country_codes=[CountryCode('US')],
        language='en',
        user=LinkTokenCreateRequestUser(
            client_user_id=user_id
        )
    )
    response = client.link_token_create(request)
    return response['link_token']

def exchange_public_token(public_token: str):
    """
    Exchanges the public token (from Plaid Link) for an access token.
    """
    request = ItemPublicTokenExchangeRequest(
        public_token=public_token
    )
    response = client.item_public_token_exchange(request)
    return response['access_token'], response['item_id']

def fetch_transactions(access_token: str, cursor: str = None):
    """
    Fetches new transactions using the /transactions/sync endpoint.
    """
    if not client:
        raise ValueError("Plaid credentials not set in .env")

    sync_request = TransactionsSyncRequest(
        access_token=access_token,
        count=100,
        cursor=cursor,
        options=TransactionsSyncRequestOptions(
            include_personal_finance_category=True
        ),
    )

    sync_response = client.transactions_sync(sync_request)
    sync_data = sync_response.to_dict() if hasattr(sync_response, "to_dict") else sync_response

    # Sandbox can occasionally return an empty initial sync; fall back to transactions/get
    if not sync_data.get("added") and cursor is None:
        start_date = datetime.date.today() - datetime.timedelta(days=30)
        end_date = datetime.date.today()

        get_request = TransactionsGetRequest(
            access_token=access_token,
            start_date=start_date,
            end_date=end_date,
            options=TransactionsGetRequestOptions(
                count=250,
                include_personal_finance_category=True,
            ),
        )
        get_response = client.transactions_get(get_request)
        get_data = get_response.to_dict() if hasattr(get_response, "to_dict") else get_response

        sync_data["added"] = get_data.get("transactions", [])
        sync_data["has_more"] = False
        sync_data["next_cursor"] = sync_data.get("next_cursor")

    return sync_data
