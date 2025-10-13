import advisor


if __name__ == "__main__":
    app = advisor.create_app()
    app.run(host="0.0.0.0", port=5000)
