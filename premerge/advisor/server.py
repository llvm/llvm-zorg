import os

import advisor


if __name__ == "__main__":
    app = advisor.create_app(
        os.environ["ADVISOR_DB_PATH"], os.environ["ADVISOR_REPO_PATH"]
    )
    app.run(host="0.0.0.0", port=5000)
