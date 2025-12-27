import os

import advisor

DEBUG_FOLDER_PATH = "/tmp/premerge_advisor_debug"


if __name__ == "__main__":
    os.mkdir(DEBUG_FOLDER_PATH)
    app = advisor.create_app(
        os.environ["ADVISOR_DB_PATH"],
        os.environ["ADVISOR_REPO_PATH"],
        DEBUG_FOLDER_PATH,
    )
    app.run(host="0.0.0.0", port=5000)
