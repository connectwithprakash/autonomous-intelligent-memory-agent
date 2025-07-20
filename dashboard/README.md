# Memory Agent Dashboard

A React-based web dashboard for visualizing and interacting with the Memory Agent system in real-time.

## Features

- **Real-time Chat Interface**: Interactive chat with the AI agent
- **Memory Visualization**: Monitor memory blocks across different storage tiers (HOT/WARM/COLD)
- **Live Statistics**: Real-time metrics including messages per minute, relevance scores, and memory usage
- **WebSocket Integration**: Live updates for all agent activities
- **Dark Mode Support**: Automatic dark/light theme based on system preferences

## Components

### Chat Tab
- Send messages to the AI agent
- View conversation history
- See token usage and correction counts
- Real-time message streaming

### Memory Tab
- Pie chart showing storage distribution across tiers
- Bar chart displaying memory usage by tier
- Table of recent memory blocks with relevance scores
- Filter blocks by storage tier
- Monitor compression ratios and age ranges

### Statistics Tab
- Real-time performance metrics
- Time series charts for:
  - Messages per minute
  - Average relevance score trends
  - Memory usage over time
- WebSocket connection status
- Active session monitoring

## Technology Stack

- **React 19** with TypeScript
- **Vite** for fast development and building
- **Tailwind CSS** for styling
- **Recharts** for data visualization
- **Lucide React** for icons
- **Axios** for API communication
- **react-use-websocket** for WebSocket connections

## Getting Started

1. Install dependencies:
   ```bash
   cd dashboard/dashboard
   npm install
   ```

2. Start the development server:
   ```bash
   npm run dev
   ```

3. Open http://localhost:5173 in your browser

## Configuration

The dashboard connects to the API server at `http://localhost:8000` by default. To change this, set the `VITE_API_URL` environment variable:

```bash
VITE_API_URL=http://your-api-server:port npm run dev
```

## Building for Production

```bash
npm run build
```

The built files will be in the `dist` directory.

## Architecture

The dashboard follows a component-based architecture:

```
src/
├── components/        # React components
│   ├── Layout.tsx    # Main layout with navigation
│   ├── Chat.tsx      # Chat interface
│   ├── Memory.tsx    # Memory visualization
│   └── Statistics.tsx # Real-time statistics
├── lib/              # Utilities and API
│   ├── api.ts        # API client and types
│   ├── websocket.ts  # WebSocket event types
│   └── utils.ts      # Helper functions
└── App.tsx           # Main application component
```

## Development

The dashboard uses:
- TypeScript for type safety
- ESLint for code quality
- Tailwind CSS for consistent styling
- Vite's HMR for fast development

## Future Enhancements

- [ ] Message search and filtering
- [ ] Memory block details modal
- [ ] Export conversation history
- [ ] Custom relevance threshold settings
- [ ] Multi-session management
- [ ] Performance profiling tools