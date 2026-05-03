import os
import stripe
from flask import Flask, request
from dotenv import load_dotenv
from storage import mark_user_paid

load_dotenv()

app = Flask(__name__)

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
endpoint_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")


@app.route("/stripe/webhook", methods=["POST"])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except Exception as e:
        return {"error": str(e)}, 400

    # УСПЕШНАЯ ОПЛАТА
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]

        metadata = session["metadata"]
        user_id = metadata["user_id"] if "user_id" in metadata else None

        if not user_id:
            print("[STRIPE] No user_id in metadata, skipping")
            return {"status": "ok"}, 200

        mark_user_paid(user_id)

        print(f"[STRIPE] User upgraded: {user_id}")

    return {"status": "ok"}, 200


if __name__ == "__main__":
    app.run(port=4242)