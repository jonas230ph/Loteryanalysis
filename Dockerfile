# Render only serves the already-prepared Supabase snapshot, so the image
# contains the lightweight standard-library mobile API rather than the scraper.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app/my_scraper
COPY my_scraper/mobile_api ./mobile_api

EXPOSE 8080
CMD ["python", "-m", "mobile_api.app"]
