# MoeMail Pool

A lightweight auto mail pool and verification code polling service based on MoeMail OpenAPI.

## Features
- Ephemeral email pool management
- Automatic email generation with expiry
- Regex-based verification code polling

## Configuration (.env)
```env
MOEMAIL_BASE=https://your-moemail.domain
MOEMAIL_KEY=your_api_key_here
MOEMAIL_DOMAIN=
```

## Run
```bash
docker compose up -d
```
