from fastapi import APIRouter, Request, HTTPException

webhook_router = APIRouter()

@webhook_router.post("/teams/webhook")
async def handle_teams_webhook(request: Request):
    """
    Handles incoming notifications from Microsoft Teams (e.g. Call started, ended).
    """
    payload = await request.json()
    print("Received Webhook from Teams:", payload)
    
    # Process event types
    # e.g. payload['value'][0]['resourceData']['state'] == 'established'
    
    return {"status": "accepted"}
