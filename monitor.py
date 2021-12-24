import subprocess
import time


def main():
    # docker run --rm -d -it --memory="300m" malaknoyn/clf
    # docker run --rm -d -it --memory="300m" malaknoyn/clf
    # docker run --rm -d -it --memory="300m" malaknoyn/clf
    # docker run --rm -d -it --memory="200m" --env PS_KEY=vHkdgDUB7WIa
    subprocess.call(["docker", "run", '--rm', "-d", "-it", "--memory=256m", "--memory-swap=0",
                    '--env', 'PS_KEY=vHkdgDUB7WIa', '--name', 'worker-1', 'malaknoyn/clf'])
    subprocess.call(["docker", "run", '--rm', "-d", "-it", "--memory=256m", "--memory-swap=0",
                    '--env', 'PS_KEY=vHkdgDUB7WIa', '--name', 'worker-2', 'malaknoyn/clf'])
    time.sleep(1800)
    subprocess.call(["docker", "container", 'stop', "worker-1"])
    subprocess.call(["docker", "container", 'stop', "worker-2"])


if __name__ == "__main__":
    main()
