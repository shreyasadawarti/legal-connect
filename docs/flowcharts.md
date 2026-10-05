# Legal Connect — Flowcharts

## Authentication Flow

```mermaid
flowchart TD
    A[User submits credentials] --> B{Valid?}
    B -- No --> C[401 Unauthorized]
    B -- Yes --> D[Issue JWT tokens]
    D --> E[Store tokens client-side]
    E --> F[Access protected APIs]
    F --> G{Token expired?}
    G -- Yes --> H[Use refresh token]
    H --> I{Refresh valid?}
    I -- Yes --> D
    I -- No --> J[Redirect to login]
```

## Appointment Booking Flow

```mermaid
flowchart TD
    A[User selects lawyer + time] --> B{Lawyer verified & available?}
    B -- No --> C[Reject booking]
    B -- Yes --> D{Slot already booked?}
    D -- Yes --> C
    D -- No --> E[Create PENDING appointment]
    E --> F[Payment (demo)]
    F --> G[Lawyer accepts/rejects]
    G -- Rejected --> H[Notify user]
    G -- Accepted --> I[CONFIRMED]
    I --> J[Eligible for chat/video]
```

*(Additional flows added per phase.)*
