# NovaTech Solutions — Encryption Standard

Document ID: NTS-SEC-STD-003
Classification: Internal Security Standard — Synthetic Demo Data
Version: 1.2
Effective Date: 1 February 2026

## Objective
This standard establishes requirements for protecting sensitive information through encryption and secure transmission.

## Data in Transit
Supported service communications across untrusted networks use TLS-based encrypted transport.

## Data at Rest
Sensitive data stored within supported managed environments is protected using approved encryption mechanisms.

## Key Management
Cryptographic keys are managed using approved services or procedures with access restricted to authorized personnel and systems.

## Application Responsibilities
Application teams must not hard-code production secrets or cryptographic keys in source code. Secrets must be managed through approved configuration or secret-management mechanisms.

## Limitation
The exact encryption configuration may vary by customer architecture, cloud provider and contractual requirements.
