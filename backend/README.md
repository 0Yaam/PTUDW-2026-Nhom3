# Culinary Blog API

This folder contains the FastAPI backend. Use the root [README](../README.md) for setup and test commands.

The API includes categories plus local registration and login under `/api/v1/auth`.

Set `JWT_SECRET` to a long random value outside development. Passwords use
PBKDF2-HMACSHA512 with 210,000 iterations; refresh tokens are stored only as SHA-256 hashes.
