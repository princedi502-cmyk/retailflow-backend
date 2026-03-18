# RetailFlow Backend

A comprehensive retail management API built with FastAPI and MongoDB Atlas.

## Features

- **Authentication & Authorization**: JWT-based auth with role-based access control
- **Product Management**: CRUD operations for products with inventory tracking
- **Order Management**: Complete order lifecycle management
- **Supplier Management**: Supplier information and relationship management
- **Analytics**: Business intelligence and reporting
- **Real-time Updates**: WebSocket support for live data
- **Security**: Rate limiting, input validation, security logging
- **Monitoring**: Database performance monitoring and health checks

## Tech Stack

- **Backend**: FastAPI (Python 3.10)
- **Database**: MongoDB Atlas
- **Authentication**: JWT with refresh tokens
- **Caching**: Redis (disabled in production)
- **Deployment**: Railway

## Environment Setup

### Development

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. Start the development server:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Production Deployment

The application is configured for Railway deployment with:

- **Automatic environment detection** (Production vs Development)
- **MongoDB Atlas connection** with fallback to local in development
- **Health checks** and monitoring
- **Optimized startup script** for production

#### Environment Variables

Production environment variables are set in Railway dashboard:

- `MONGO_URL`: MongoDB Atlas connection string
- `DATABASE_NAME`: Database name
- `SECRET_KEY`: JWT secret key
- `ENVIRONMENT`: Set to "production"
- `RAILWAY_ENVIRONMENT`: Set to "production"

## API Documentation

Once running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

## Database Connection Strategy

The application uses a smart connection strategy:

### Production
- **Primary**: MongoDB Atlas with robust SSL settings
- **Fallback**: None (fails fast to alert issues)

### Development
- **Primary**: MongoDB Atlas with relaxed SSL settings
- **Fallback**: Local MongoDB instance

This ensures:
- ✅ Production reliability with Atlas
- ✅ Development flexibility with local fallback
- ✅ Proper SSL handling in both environments

## API Endpoints

### Authentication
- `POST /auth/register` - User registration
- `POST /auth/login` - User login
- `POST /auth/refresh` - Token refresh
- `POST /auth/verify-email` - Email verification
- `GET /auth/dev/verification-tokens` - Dev endpoint for tokens

### Products
- `GET /products/` - List products
- `POST /products/` - Create product (owner only)
- `GET /products/{id}` - Get product
- `PUT /products/{id}` - Update product (owner only)
- `DELETE /products/{id}` - Delete product (employee+)

### Orders
- `GET /orders/` - List orders
- `POST /orders/` - Create order
- `GET /orders/{id}` - Get order
- `PUT /orders/{id}` - Update order

### Analytics
- `GET /analytics/dashboard` - Dashboard stats
- `GET /analytics/sales` - Sales analytics
- `GET /analytics/inventory` - Inventory reports

## Security Features

- **Rate Limiting**: 60 requests per minute per IP
- **Input Validation**: Comprehensive request validation
- **Security Headers**: XSS, CSRF, and clickjacking protection
- **Audit Logging**: Security event logging
- **Role-based Access**: Admin, Owner, Employee roles

## Monitoring

### Health Checks
- `GET /health` - Application health status
- Database connectivity check
- Service availability monitoring

### Database Monitoring
- Connection pool monitoring
- Query performance tracking
- Slow query logging
- Memory usage tracking

## Development Tips

### Email Verification (Development)
Use the development endpoint to get verification tokens:
```bash
curl http://localhost:8000/auth/dev/verification-tokens
```

### Test Users
Create users with different roles for testing:
- **Admin**: Full system access
- **Owner**: Can manage products and orders
- **Employee**: Can view and manage orders

## Deployment

### Railway
1. Connect repository to Railway
2. Set environment variables in Railway dashboard
3. Deploy - Railway will automatically detect and build

### Docker
```bash
docker build -t retailflow-backend .
docker run -p 8000:8000 retailflow-backend
```

## Troubleshooting

### MongoDB Connection Issues
- **Development**: Falls back to local MongoDB if Atlas fails
- **Production**: Check Atlas IP whitelist and network access
- **SSL Issues**: Verify certificate settings in Atlas

### Common Issues
- **Port conflicts**: Ensure PORT environment variable is set
- **CORS errors**: Check ALLOWED_ORIGINS in configuration
- **Rate limiting**: Adjust RATE_LIMIT_PER_MINUTE if needed

## License

© 2024 RetailFlow. All rights reserved.
