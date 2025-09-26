from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# -----------------
# 1. Pydantic Models (Data Structure/Validation)
# -----------------

# Define the structure and types for incoming request data
class Item(BaseModel):
    """Schema for an item resource."""
    name: str
    price: float
    is_offer: Optional[bool] = None  # Optional field with a default of None

# -----------------
# 2. Application Setup
# -----------------

# Create the FastAPI application instance
app = FastAPI(
    title="Minimal FastAPI Template",
    description="A simple API demonstrating GET and POST methods.",
    version="1.0.0"
)

# -----------------
# 3. Routes (Endpoints)
# -----------------

# GET Endpoint: Root Path
@app.get("/")
async def read_root():
    """Returns a simple welcome message."""
    return {"message": "Welcome to the FastAPI Template!"}

# GET Endpoint: Path Parameters
@app.get("/items/{item_id}")
async def read_item(item_id: int):
    """Retrieves an item by its ID (example only)."""
    if item_id < 1:
        # FastAPI handles exceptions gracefully
        raise HTTPException(status_code=400, detail="Item ID must be positive")
    return {"item_id": item_id, "name": f"Item {item_id}"}

# POST Endpoint: Request Body
@app.post("/items/")
async def create_item(item: Item):
    """Creates a new item using the Pydantic Item model for validation."""
    
    # The 'item' variable is a validated Python object (Pydantic model)
    # You would typically save this data to your PostgreSQL database here.
    
    # For demonstration: return the received data
    return {
        "status": "Item received",
        "name": item.name,
        "price": item.price,
        "is_offer": item.is_offer
    }

# Run with: uvicorn app.main:app --reload