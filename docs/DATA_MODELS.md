# Data Models

## Database Schema
```mermaid
erDiagram
    USERS ||--o{ ASSESSMENTS : has
    USERS {
        int id PK
        string username
        string email
    }
    ASSESSMENTS {
        int id PK
        int user_id FK
        float burnout_score
    }