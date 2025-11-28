import os
import datetime
import plaid
from plaid.api import plaid_api
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.transactions_sync_request import TransactionsSyncRequest
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
    # Prepare arguments, omitting cursor if it is None
    kwargs = {
        'access_token': access_token,
        'count': 100
    }
    if cursor:
        kwargs['cursor'] = cursor
        
    request = TransactionsSyncRequest(**kwargs)
    response = client.transactions_sync(request)
    return response
