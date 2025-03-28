# Botify React Frontend

This is a React-based frontend application for interacting with the Botify bot service. It provides functionality similar to the existing Streamlit frontend.

## Features

- Home page with project information
- Chat interface for conversational interaction with the bot
- Single question interface for one-off questions with search results

## Getting Started

### Prerequisites

- Node.js (v14 or higher)
- npm or yarn
- Botify bot service running (default: http://localhost:8000)

### Installation

1. Install dependencies:

```bash
npm install
```

2. Create a `.env` file in the root directory with the following content:

```
REACT_APP_API_URL=http://localhost:8000
```

Adjust the URL to match your bot service endpoint.

### Running the Application

```bash
npm start
```

The application will be available at http://localhost:3000

### Building for Production

```bash
npm run build
```

This will create a production-ready build in the `build` directory.

## Docker Support

The application can also be run using Docker:

```bash
# Build the Docker image
docker build -t botify-react-frontend .

# Run the container
docker run -p 3000:80 -e REACT_APP_API_URL=http://localhost:8000 botify-react-frontend
```

## Project Structure

- `src/` - Application source code
  - `components/` - Reusable UI components
  - `pages/` - Page components (Home, Chat, SingleQuestion)
  - `helpers/` - Utility functions and API calls
- `public/` - Static assets

## Contributing

Please see the main [Botify repository](https://github.com/retaildevcrews/botify/) for contribution guidelines.