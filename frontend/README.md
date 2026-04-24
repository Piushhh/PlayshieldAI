# PlayshieldAI — Responsive Editorial Interface

> A high-performance, Next.js frontend built for the PlayshieldAI V2 platform. Features a brutalist editorial design system optimized for high-density data visualization and AI-native workflows.

## 🎨 Design Philosophy

PlayshieldAI utilizes a custom **Brutalist Editorial Grid** system:
- **Typography-First**: Leveraging high-contrast scales and `clamp()` for fluid, responsive typography.
- **Information Density**: Side-by-side panel systems that stack intelligently for mobile review workflows.
- **AI-Native Callouts**: Specialized UI components for displaying Gemini rationales and auditable draft revisions without breaking the reviewer's cognitive flow.

## 🛠️ Tech Stack

- **Framework**: [Next.js 14+](https://nextjs.org) (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS with custom editorial utility classes.
- **Data Fetching**: Axios-based API client with standardized error handling and defensive optional chaining.
- **Visualization**: Recharts for responsive detection trends and confidence distributions.

## 🚀 Getting Started

### 1. Installation
```bash
npm install
```

### 2. Environment Configuration
Create a `.env.local` file:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Run Development Server
```bash
npm run dev
```

## 🚢 Production Deployment

The frontend is containerized via `Dockerfile.prod` and deployed to **Google Cloud Run**.

### Manual Deploy
```bash
gcloud run deploy playshield-frontend \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated
```

## 🛡️ Defensive Development

The V2 frontend implements **strict defensive patterns** to handle legacy production data:
- **Nullish Coalescing**: Ensuring UI components never crash on missing AI metadata.
- **Responsive Grids**: All quadrant grids (Confidence, Risk, Case State) use responsive `sm:grid-cols-2` and `xl:grid-cols-2` layouts with overflow-hidden protection.
- **Global Error States**: Standardized `ErrorState` and `Skeleton` loaders for all async views.
