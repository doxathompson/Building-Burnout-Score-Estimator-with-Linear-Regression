# System Architecture

## Overview
```mermaid
flowchart TD
    A[Frontend] --> B[Backend]
    B --> C[Database]
```
![Detailed Architecture](diagrams/images/architecture.png)

## Components
| Component       | Description                          |
|-----------------|--------------------------------------|
| Streamlit UI    | User interface with input forms      |
| Prediction Model| Trained sklearn linear regression    |