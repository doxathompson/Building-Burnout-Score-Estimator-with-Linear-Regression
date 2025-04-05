# Assessment Workflow

## Prediction Process
```mermaid
sequenceDiagram
    User->>UI: Enter Work/Sleep Data
    UI->>Model: Get Prediction
    Model-->>UI: Return Score
```

## Error Handling
![Error Flow](diagrams/images/error_flow.png)