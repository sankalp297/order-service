# from fastapi import FastAPI
# from prometheus_fastapi_instrumentator import Instrumentator
#
# app = FastAPI(title="Order Service")
#
# # This auto-generates metrics like request count, latency etc.
# # Kubernetes monitoring tools (Prometheus) will read these later
# Instrumentator().instrument(app).expose(app)
#
# # Simple in-memory storage (like a Python dictionary acting as database)
# orders = {}
# order_counter = 0
#
#
# @app.get("/health")
# def health():
#     """Kubernetes will hit this every 10 sec to check: is this app alive?"""
#     return {"status": "ok"}
#
#
# @app.get("/ready")
# def ready():
#     """Kubernetes checks this to know: is this app ready to receive traffic?"""
#     return {"status": "ready"}
#
#
# @app.post("/orders")
# def create_order(product_id: str, quantity: int):
#     """Create a new order"""
#     global order_counter
#     order_counter += 1
#     orders[order_counter] = {
#         "product_id": product_id,
#         "quantity": quantity,
#         "status": "created"
#     }
#     return {"order_id": order_counter, **orders[order_counter]}
#
#
# @app.get("/orders/{order_id}")
# def get_order(order_id: int):
#     """Get order by ID"""
#     if order_id in orders:
#         return {"order_id": order_id, **orders[order_id]}
#     return {"error": "order not found"}
#
#
# @app.get("/orders")
# def list_orders():
#     """List all orders"""
#     return orders

import httpx
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from app.config import INVENTORY_URL

app = FastAPI(title="Order Service")
Instrumentator().instrument(app).expose(app)

orders = {}
order_counter = 0


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready():
    return {"status": "ready"}


@app.post("/orders")
def create_order(product_id: str, quantity: int):
    global order_counter

    # Call inventory-service to check stock
    try:
        response = httpx.get(f"{INVENTORY_URL}/inventory/{product_id}")
        if response.status_code == 404:
            return {"error": f"product '{product_id}' not found in inventory"}

        stock_info = response.json()
        if stock_info["stock"] < quantity:
            return {"error": "insufficient stock", "available": stock_info["stock"]}

        # Reserve the stock
        httpx.put(
            f"{INVENTORY_URL}/inventory/{product_id}/reserve",
            json={"quantity": quantity},
        )
    except Exception as e:
        return {"error": f"inventory service unavailable: {str(e)}"}

    order_counter += 1
    orders[order_counter] = {
        "product_id": product_id,
        "quantity": quantity,
        "status": "confirmed",
    }
    return {"order_id": order_counter, **orders[order_counter]}


@app.get("/orders/{order_id}")
def get_order(order_id: int):
    if order_id in orders:
        return {"order_id": order_id, **orders[order_id]}
    return {"error": "order not found"}


@app.get("/orders")
def list_orders():
    return orders
