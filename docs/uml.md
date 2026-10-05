# Legal Connect — UML Diagrams

Diagrams below use Mermaid syntax and will be expanded as the corresponding phases are built.

## Use Case Overview

```mermaid
flowchart LR
    U[Citizen] --> S[Search Lawyers]
    U --> B[Book Appointment]
    U --> C[Chat with Lawyer]
    U --> D[Upload Documents]
    U --> AI[AI Assistant]
    L[Lawyer] --> V[Manage Availability]
    L --> R[Accept/Reject Appointments]
    L --> VID[Video Consultation]
    A[Admin] --> VER[Verify Lawyers]
    A --> COMP[Manage Complaints]
```

*(Detailed sequence, class, and activity diagrams added per phase.)*
