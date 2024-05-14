import os
from datetime import datetime as dt

import jasnah


def main():
    now = dt.now()
    assigned_supervisors = os.environ.get("ASSIGNED_SUPERVISORS", None)
    me = jasnah.CONFIG.supervisor_id
    with open("/home/setup/.supervisor.txt", "a") as f:
        print("Test", now, me, assigned_supervisors, file=f)


if __name__ == "__main__":
    main()
