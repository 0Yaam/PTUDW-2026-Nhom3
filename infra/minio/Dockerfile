# The former minio/minio registry image is no longer publicly pullable.
# Build the official, pinned source release for local development instead.
FROM golang:1.24-bookworm AS build
ARG MINIO_VERSION=RELEASE.2025-10-15T17-29-55Z
ENV GOBIN=/out CGO_ENABLED=0
RUN go install github.com/minio/minio@${MINIO_VERSION}

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY --from=build /out/minio /usr/local/bin/minio
EXPOSE 9000 9001
VOLUME ["/data"]
ENTRYPOINT ["minio"]
