FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV production
ENV PORT 3000
ENV HOSTNAME "0.0.0.0"

# Create non-root user
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# We expect the host (Mac) to have run 'npm run build'
# and generated the standalone output.
# The sync script will put these in the correct place.
COPY . ./
# Next.js standalone output contains everything needed to run:
# node_modules (production only), .next/server, server.js, etc.

USER nextjs

EXPOSE 3000

CMD ["node", "server.js"]
