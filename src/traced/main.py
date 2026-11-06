import uvicorn


def run() -> None:
    uvicorn.run("traced.api:app", host="0.0.0.0", port=8080)


if __name__ == "__main__":
    run()

