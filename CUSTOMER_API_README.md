# Customer Management API Documentation

This document provides comprehensive documentation for the Customer Management API endpoints, data structures, and usage examples.

## Overview

The Customer Management API provides full CRUD operations for customer data, including advanced search, order history tracking, and soft delete functionality. It follows a clean architecture pattern with separate layers for models, schemas, services, and API endpoints.

## API Endpoints

### Base URL
```
/customers
```

### 1. Create Customer
**POST** `/customers/`

Create a new customer in the system.

#### Request Body
```json
{
  "name": "John Doe",
  "email": "john.doe@example.com",
  "phone": "+1234567890",
  "address": "123 Main St",
  "city": "New York",
  "state": "NY",
  "postal_code": "10001",
  "country": "USA",
  "is_active": true
}
```

#### Response
```json
{
  "id": "507f1f77bcf86cd799439011",
  "name": "John Doe",
  "email": "john.doe@example.com",
  "phone": "+1234567890",
  "address": "123 Main St",
  "city": "New York",
  "state": "NY",
  "postal_code": "10001",
  "country": "USA",
  "is_active": true,
  "created_at": "2024-03-24T10:30:00Z",
  "updated_at": "2024-03-24T10:30:00Z",
  "total_orders": 0,
  "total_spent": 0.0
}
```

#### Validation Rules
- `name`: Required, 1-100 characters
- `email`: Required, valid email format, must be unique
- `phone`: Required, 10-20 characters, must be unique
- `address`: Optional, max 200 characters
- `city`: Optional, max 50 characters
- `state`: Optional, max 50 characters
- `postal_code`: Optional, max 20 characters
- `country`: Optional, max 50 characters
- `is_active`: Optional, boolean (default: true)

---

### 2. List Customers
**GET** `/customers/`

Retrieve paginated list of customers with optional filtering.

#### Query Parameters
- `page`: Page number (default: 1, min: 1)
- `limit`: Items per page (default: 10, min: 1, max: 100)
- `is_active`: Filter by active status (optional, true/false)

#### Response
```json
{
  "customers": [
    {
      "id": "507f1f77bcf86cd799439011",
      "name": "John Doe",
      "email": "john.doe@example.com",
      "phone": "+1234567890",
      "address": "123 Main St",
      "city": "New York",
      "state": "NY",
      "postal_code": "10001",
      "country": "USA",
      "is_active": true,
      "created_at": "2024-03-24T10:30:00Z",
      "updated_at": "2024-03-24T10:30:00Z",
      "total_orders": 5,
      "total_spent": 1250.75
    }
  ],
  "total_count": 150,
  "page": 1,
  "limit": 10,
  "total_pages": 15
}
```

---

### 3. Get Customer by ID
**GET** `/customers/{customer_id}`

Retrieve detailed information for a specific customer.

#### Path Parameters
- `customer_id`: MongoDB ObjectId of the customer

#### Response
```json
{
  "id": "507f1f77bcf86cd799439011",
  "name": "John Doe",
  "email": "john.doe@example.com",
  "phone": "+1234567890",
  "address": "123 Main St",
  "city": "New York",
  "state": "NY",
  "postal_code": "10001",
  "country": "USA",
  "is_active": true,
  "created_at": "2024-03-24T10:30:00Z",
  "updated_at": "2024-03-24T10:30:00Z",
  "total_orders": 5,
  "total_spent": 1250.75
}
```

---

### 4. Update Customer
**PUT** `/customers/{customer_id}`

Update customer information. Only provided fields will be updated.

#### Path Parameters
- `customer_id`: MongoDB ObjectId of the customer

#### Request Body
```json
{
  "name": "John Smith",
  "email": "john.smith@example.com",
  "city": "Los Angeles"
}
```

#### Response
```json
{
  "id": "507f1f77bcf86cd799439011",
  "name": "John Smith",
  "email": "john.smith@example.com",
  "phone": "+1234567890",
  "address": "123 Main St",
  "city": "Los Angeles",
  "state": "NY",
  "postal_code": "10001",
  "country": "USA",
  "is_active": true,
  "created_at": "2024-03-24T10:30:00Z",
  "updated_at": "2024-03-24T11:00:00Z",
  "total_orders": 5,
  "total_spent": 1250.75
}
```

---

### 5. Delete Customer
**DELETE** `/customers/{customer_id}`

Soft delete a customer by setting `is_active` to false. Customer data is preserved for order history and analytics.

#### Path Parameters
- `customer_id`: MongoDB ObjectId of the customer

#### Response
```json
{
  "message": "Customer deleted successfully"
}
```

---

### 6. Search Customers
**GET** `/customers/search`

Search customers by name, email, or phone number using case-insensitive regex matching.

#### Query Parameters
- `q`: Search query (required, min 1 character)
- `page`: Page number (default: 1, min: 1)
- `limit`: Items per page (default: 10, min: 1, max: 100)

#### Example Request
```
GET /customers/search?q=john&page=1&limit=10
```

#### Response
```json
{
  "customers": [
    {
      "id": "507f1f77bcf86cd799439011",
      "name": "John Doe",
      "email": "john.doe@example.com",
      "phone": "+1234567890",
      "address": "123 Main St",
      "city": "New York",
      "state": "NY",
      "postal_code": "10001",
      "country": "USA",
      "is_active": true,
      "created_at": "2024-03-24T10:30:00Z",
      "updated_at": "2024-03-24T10:30:00Z",
      "total_orders": 5,
      "total_spent": 1250.75
    }
  ],
  "total_count": 3
}
```

---

### 7. Get Customer Order History
**GET** `/customers/{customer_id}/orders`

Retrieve order history for a specific customer with pagination.

#### Path Parameters
- `customer_id`: MongoDB ObjectId of the customer

#### Query Parameters
- `page`: Page number (default: 1, min: 1)
- `limit`: Orders per page (default: 10, min: 1, max: 100)

#### Response
```json
{
  "customer_id": "507f1f77bcf86cd799439011",
  "orders": [
    {
      "id": "507f1f77bcf86cd799439012",
      "created_at": "2024-03-24T09:15:00Z",
      "total_price": 250.50,
      "status": "completed",
      "items": [
        {
          "product_id": "507f1f77bcf86cd799439013",
          "product_name": "Product A",
          "quantity": 2,
          "price": 125.25,
          "total": 250.50
        }
      ]
    }
  ],
  "total_orders": 5,
  "total_spent": 1250.75
}
```

## Data Models

### Customer Schema
```python
class CustomerBase(BaseModel):
    name: str                    # Customer full name
    email: str                   # Valid email address (unique)
    phone: str                   # Phone number (unique)
    address: Optional[str]       # Street address
    city: Optional[str]          # City name
    state: Optional[str]         # State or province
    postal_code: Optional[str]   # Postal or ZIP code
    country: Optional[str]       # Country name
    is_active: bool              # Account status
```

### Additional Fields (System-managed)
- `id`: MongoDB ObjectId string
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp
- `total_orders`: Number of orders (auto-calculated)
- `total_spent`: Total amount spent (auto-calculated)

## Database Schema

### Collection: `customers`

```javascript
{
  _id: ObjectId("507f1f77bcf86cd799439011"),
  name: "John Doe",
  email: "john.doe@example.com",
  phone: "+1234567890",
  address: "123 Main St",
  city: "New York",
  state: "NY",
  postal_code: "10001",
  country: "USA",
  is_active: true,
  created_at: ISODate("2024-03-24T10:30:00Z"),
  updated_at: ISODate("2024-03-24T10:30:00Z"),
  total_orders: 5,
  total_spent: 1250.75
}
```

## Database Indexes

The following indexes are automatically created for optimal performance:

1. **Unique Email Index**: `{"email": 1}` - Fast email lookups and uniqueness
2. **Unique Phone Index**: `{"phone": 1}` - Fast phone lookups and uniqueness
3. **Created At Index**: `{"created_at": -1}` - Pagination sorting
4. **Active Status Index**: `{"is_active": 1}` - Active/inactive filtering
5. **Compound Active/Created Index**: `{"is_active": 1, "created_at": -1}` - Active customer pagination
6. **Text Search Index**: `{"name": "text", "email": "text", "phone": "text"}` - Search functionality
7. **Total Orders Index**: `{"total_orders": -1}` - Customer analytics
8. **Total Spent Index**: `{"total_spent": -1}` - Customer analytics

## Error Handling

### Common HTTP Status Codes

- `200 OK`: Request successful
- `201 Created`: Customer created successfully
- `400 Bad Request`: Invalid input data or validation error
- `404 Not Found`: Customer not found
- `409 Conflict`: Duplicate email or phone
- `500 Internal Server Error`: Server error

### Error Response Format
```json
{
  "detail": "Error message describing what went wrong"
}
```

## Security

### Authentication
All endpoints require authentication via JWT token. Include the token in the Authorization header:

```
Authorization: Bearer <your_jwt_token>
```

### Authorization
Only authenticated users can access customer management endpoints. Role-based access control can be implemented as needed.

## Testing

### Running Tests
```bash
cd retailflow-backend
python test_customer_api.py
```

### Test Coverage
- ✅ Customer creation with validation
- ✅ Duplicate prevention (email/phone)
- ✅ Customer listing with pagination
- ✅ Customer retrieval by ID
- ✅ Customer updates
- ✅ Customer search functionality
- ✅ Soft delete functionality
- ✅ Order history retrieval
- ✅ Active/inactive filtering

## Performance Considerations

1. **Pagination**: Always use pagination for large datasets
2. **Indexing**: All queries are optimized with appropriate indexes
3. **Soft Delete**: Preserves data integrity while hiding inactive customers
4. **Caching**: Consider implementing Redis caching for frequently accessed customers
5. **Connection Pooling**: MongoDB connection pooling is configured for optimal performance

## Integration Examples

### JavaScript/Node.js
```javascript
// Create a new customer
const response = await fetch('/customers/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    name: 'John Doe',
    email: 'john@example.com',
    phone: '+1234567890'
  })
});

const customer = await response.json();
```

### Python
```python
import requests

# Create a new customer
response = requests.post(
  'http://localhost:8000/customers/',
  json={
    'name': 'John Doe',
    'email': 'john@example.com',
    'phone': '+1234567890'
  },
  headers={'Authorization': f'Bearer {token}'}
)

customer = response.json()
```

## File Structure

```
app/
├── models/
│   └── customer_model.py          # Pydantic models
├── schemas/
│   └── customer_schema.py         # API schemas
├── services/
│   └── customer_service.py        # Business logic
├── api/router/
│   └── customers.py               # API endpoints
└── db/
    └── customer_indexes.py        # Database indexes
```

This comprehensive structure ensures separation of concerns, maintainability, and scalability of the customer management system.
