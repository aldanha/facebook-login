from fastapi import FastAPI, Request, HTTPException, Response
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()


CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
FACEBOOK_OAUTH_URL = "https://www.facebook.com/v19.0/dialog/oauth"
FACEBOOK_TOKEN_URL = "https://graph.facebook.com/v19.0/oauth/access_token"
FACEBOOK_USER_DATA_URL = "https://graph.facebook.com/v19.0/me/accounts"
FB_MESSENGER_API_BASE = "https://graph.facebook.com/v19.0/me/messages"
FB_VERIFY_TOKEN = os.getenv("FB_VERIFY_TOKEN")

scope = "email," \
        "pages_show_list," \
        "business_management," \
        "pages_manage_engagement," \
        "pages_read_engagement," \
        "public_profile," \
        "pages_manage_posts," \
        "pages_messaging," \
        "pages_manage_metadata," \
        "instagram_manage_messages," \
        "instagram_basic"

user_session = {}


@app.get("/")
async def home():
    return {"message": "Hello, visit /login to authenticate with Facebook"}


@app.get("/login")
async def login():

    auth_url = f"{FACEBOOK_OAUTH_URL}?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&state=12345&scope={scope}"

    return Response(status_code=303, headers={"Location": auth_url})


@app.get("/auth/facebook/callback")
async def facebook_callback(state: str, code: str):
    token_response = await exchange_code_for_token(code)
    if "access_token" not in token_response:
        raise HTTPException(status_code=400, detail="Failed to obtain access token")

    user_data = await fetch_user_data(token_response["access_token"])
    print("token response :", token_response)
    print ("user data: ", user_data)
    access_token = user_data["data"][0]["access_token"]
    page_id = user_data["data"][0]["id"]
    user_session["page_access_token"]=access_token
    user_session["page_id"]=page_id
    subscription_response = await subscribe_to_webhook(page_id, access_token)
    print("user: ", user_session)
    return {"user_data: ": user_data,
            "subscription_response ": subscription_response}


async def subscribe_to_webhook(page_id: str, page_access_token: str):
    subscribe_url = f"https://graph.facebook.com/{page_id}/subscribed_apps"
    async with httpx.AsyncClient() as client:
        response = await client.post(
            subscribe_url,
            params={
                "subscribed_fields": "messages, messaging_postbacks",
                "access_token": page_access_token,
            }
        )
    return response.json()


async def exchange_code_for_token(code: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            FACEBOOK_TOKEN_URL,
            params={
                "client_id": CLIENT_ID,
                "redirect_uri": REDIRECT_URI,
                "client_secret": CLIENT_SECRET,
                "code": code,
            },
        )
        print ("response: ", response)
    return response.json()


async def fetch_user_data(access_token: str):
    async with httpx.AsyncClient() as client:
        print(access_token)
        response = await client.get(
            FACEBOOK_USER_DATA_URL,
            params={"access_token": access_token},
        )
        print(response)
    return response.json()


@app.get('/webhook')
def init_messenger(request: Request):
    fb_token = request.query_params.get("hub.verify_token")
    print(fb_token)
    if fb_token == FB_VERIFY_TOKEN:
        return Response(content=request.query_params["hub.challenge"])
    return 'Failed to verify token'


@app.post("/webhook")
async def receive_facebook_webhook(request: Request):
    webhook_event = await request.json()
    print("Received webhook event:", webhook_event)

    return Response(status_code=200)
