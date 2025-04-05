# API Documentation

## Prediction Endpoint
`POST /predict`
```json
{
  "work_hours": 9,
  "sleep_hours": 7,
  "exercise_minutes": 30
}
```

## Response
```json
{
  "score": 65.2,
  "risk_level": "moderate",
  "recommendations": ["Take more breaks"]
}
```