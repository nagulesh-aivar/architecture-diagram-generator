# Frontend Dockerfile for Architecture Diagram Generator
FROM node:20-alpine

# Set working directory
WORKDIR /app

# Copy package files
COPY Frontend/package.json Frontend/package-lock.json* ./

# Install dependencies
RUN npm ci

# Copy frontend source code
COPY Frontend/ ./

# Expose port
EXPOSE 3000

# Set environment variables
ENV NODE_ENV=development
ENV VITE_API_URL=http://localhost:8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD node -e "require('http').get('http://localhost:3000', (r) => {process.exit(r.statusCode === 200 ? 0 : 1)})" || exit 1

# Run the development server
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

