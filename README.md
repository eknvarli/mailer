# Email Classification API

FastAPI-based AI email classification system with real-time IMAP polling and machine learning analysis.

---

## Features

* Real-time email polling from IMAP servers
* AI-powered email categorization
* Multi-dimensional analysis
* JWT authentication
* RESTful API

---

## Installation

```bash
pip install -r requirements.txt
```

---

## Run Server

```bash
uvicorn main:app --reload --port 8000
```

---

## API Endpoints

### Authentication

**POST** `/auth/login`
Body:

```json
{
  "email": "user@example.com",
  "password": "password"
}
```

### Email Analysis

* **GET** `/mail/analyze?email=user@gmail.com`
* **GET** `/mail/analyze-single?text=email_content`
* **GET** `/mail/stats?email=user@gmail.com`
* **GET** `/mail/priority-emails?email=user@gmail.com&priority=high`
* **GET** `/mail/department-emails?email=user@gmail.com&department=customer_service`

### Email Polling

* **POST** `/mail/start`
  Body:

```json
{
  "server": "imap.gmail.com",
  "email": "user@gmail.com",
  "password": "app_password",
  "interval": 60
}
```

* **GET** `/mail/listen?email=user@gmail.com`

---

## Classification Categories

* **Main:** complaint, question, suggestion, information
* **Priority:** low, medium, high
* **Sentiment:** negative, neutral, positive
* **Departments:** customer_service, logistics, accounting, technical_support, marketing

---

## Example Usage

**Login to get token:**

```bash
curl -X POST "http://localhost:8000/auth/login" \
-H "Content-Type: application/json" \
-d '{"email": "user@example.com", "password": "password"}'
```

**Analyze emails:**

```bash
curl -X GET "http://localhost:8000/mail/analyze?email=test@gmail.com" \
-H "Authorization: Bearer YOUR_TOKEN"
```

**Response Example:**

```json
{
  "subject": "Damaged Product",
  "sender": "customer@example.com",
  "analysis": {
    "category": "complaint",
    "subcategory": "damaged_product",
    "priority": "high",
    "sentiment": "negative",
    "department": "customer_service",
    "confidence_score": 0.92
  }
}
```

---

## Training Data

System uses `training_data.json` with labeled examples for:

* Email body text
* Categories and subcategories
* Priority and sentiment ratings
* Department assignments
* Response templates

---

## Security

* JWT token authentication
* Secure password hashing
* IMAP over SSL
* Input validation

---

## API Documentation

Visit [http://localhost:8000/docs](http://localhost:8000/docs) for interactive API documentation when server is running.
