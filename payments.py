import os
import stripe

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


def create_checkout_session(user_id):
    session = stripe.checkout.Session.create(
        mode="payment",
        payment_method_types=["card"],
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": "Salytic Pro Access",
                    },
                    "unit_amount": 499,  # $4.99
                },
                "quantity": 1,
            }
        ],
        success_url="http://localhost:8501/?success=true",
        cancel_url="http://localhost:8501/?canceled=true",
        metadata={
            "user_id": user_id
        }
    )

    return session.url