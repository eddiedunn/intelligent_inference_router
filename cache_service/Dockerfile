FROM rust:1.77-slim AS build
WORKDIR /usr/src/app
COPY . .
RUN cargo build --release

FROM debian:bookworm-slim
WORKDIR /app
COPY --from=build /usr/src/app/target/release/cache_service /app/cache_service
EXPOSE 8600
CMD ["/app/cache_service"]
