from datetime import datetime as dt


def main():
    now = dt.now()
    with open("/home/setup/.supervisor.txt", "a") as f:
        print("Test", now, file=f)


if __name__ == "__main__":
    main()
