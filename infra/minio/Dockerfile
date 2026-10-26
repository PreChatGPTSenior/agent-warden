FROM alpine:3.22.6 AS download
ARG TARGETARCH
# Verify the official release binary against its published SHA-256 for each supported architecture.
RUN if [ -z "$TARGETARCH" ]; then \
      case "$(uname -m)" in x86_64) TARGETARCH=amd64 ;; aarch64) TARGETARCH=arm64 ;; *) exit 1 ;; esac; \
    fi \
    && case "$TARGETARCH" in \
      amd64) checksum=53e2a2cb16c5366ea6fbbc479c19ddb4c6a0948273e752f740fb1fbf27bb817c ;; \
      arm64) checksum=6c2f3142c94240206123177f4ba1e360daa5d1e0a4962e90757ef4f92c3ab57c ;; \
      *) exit 1 ;; \
    esac \
    && wget -q -O /minio "https://github.com/minio/minio/releases/download/RELEASE.2025-04-22T22-12-26Z/minio.linux-${TARGETARCH}.RELEASE.2025-04-22T22-12-26Z" \
    && echo "$checksum  /minio" | sha256sum -c - \
    && chmod 0755 /minio

FROM alpine:3.22.6
COPY --from=download /minio /usr/local/bin/minio
RUN mkdir /data && chown 10001:10001 /data
USER 10001:10001
EXPOSE 9000 9001
HEALTHCHECK --interval=5s --timeout=5s --retries=12 CMD wget -q -O /dev/null http://localhost:9000/minio/health/live || exit 1
ENTRYPOINT ["/usr/local/bin/minio"]
CMD ["server", "/data", "--console-address", ":9001"]
