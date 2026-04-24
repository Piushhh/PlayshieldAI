# Sample Data

This directory contains sample media files for testing IP Guardian.

## Demo Assets
The seed script (`backend/app/seed.py`) automatically generates sample images
for testing. In production, you would upload real media files through the UI
or API.

## Test Images
To test the system with real images, place image files here and upload them
via the API:

```bash
# Upload a sample asset
curl -X POST http://localhost:8000/assets \
  -H "Authorization: Bearer <TOKEN>" \
  -F "title=Sample Image" \
  -F "media_type=image" \
  -F "file=@sample_data/test_image.png"
```
