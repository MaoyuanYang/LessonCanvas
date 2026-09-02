# LessonCanvas Next.js Web image (F012 D1).
# Build context MUST be the repository root so the pnpm workspace installs.
FROM node:22-alpine AS deps
WORKDIR /repo
RUN corepack enable
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY apps/web/package.json apps/web/package.json
RUN pnpm install --frozen-lockfile

FROM node:22-alpine AS build
WORKDIR /repo
RUN corepack enable
COPY --from=deps /repo ./
COPY . .
# NEXT_PUBLIC_* values are inlined at build time; the deploy script passes the LAN origin.
ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL \
    NEXT_TELEMETRY_DISABLED=1
RUN pnpm web:build

FROM node:22-alpine
WORKDIR /repo
ENV NODE_ENV=production \
    PORT=3000 \
    HOSTNAME=0.0.0.0
# In a pnpm workspace the standalone output keeps the monorepo layout (app
# nested under apps/web with symlinked node_modules at the root). Copy the
# whole tree so the symlinks resolve, and run the nested server.js.
COPY --from=build /repo/apps/web/.next/standalone ./
COPY --from=build /repo/apps/web/.next/static ./apps/web/.next/static
CMD ["node", "apps/web/server.js"]
