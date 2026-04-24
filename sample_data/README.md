# PlayshieldAI — Sample Data & Asset Testing

This directory is reserved for media assets used during development, testing, and platform demonstration.

## Development Seeding

The platform includes a seeding script to populate a local development environment with mock assets and detections.

```bash
# Run from the project root
make seed
```

## Manual Asset Registration (API)

To test the platform with custom assets via the command line, use the following `curl` pattern.

### Production Registry
```bash
curl -X POST https://api.playshieldai.dev/assets \
  -H "Authorization: Bearer <YOUR_JWT_TOKEN>" \
  -F "title=Infringement Test Asset" \
  -F "media_type=image" \
  -F "license_type=all_rights_reserved" \
  -F "file=@sample_data/test_image.png"
```

### Local Development
```bash
curl -X POST http://localhost:8000/assets \
  -H "Authorization: Bearer <YOUR_JWT_TOKEN>" \
  -F "title=Sample Image" \
  -F "media_type=image" \
  -F "file=@sample_data/test_image.png"
```

## Media Specifications

For optimal detection results, ensure test images and video frames follow these guidelines:
- **Format**: PNG, JPEG, or MP4.
- **Resolution**: Minimum 224x224 (optimized for CLIP embedding extraction).
- **Metadata**: Ensure files have clear titles for registry tracking.
