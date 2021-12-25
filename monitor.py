import subprocess
import time


def main():
    # docker run --rm -d -it --memory="300m" malaknoyn/clf
    # docker run --rm -d -it --memory="300m" malaknoyn/clf
    # docker run --rm -d -it --memory="300m" malaknoyn/clf
    # docker run --rm -d -it --memory="200m" --env PS_KEY=EAsxrGZ6DY6u ps_clf
    subprocess.call(["docker", "run", '--rm', "-d", "-it", "--memory=256m", "--memory-swap=0", "--cpus=0.5",
                    '--env', 'PS_KEY=EAsxrGZ6DY6u', '--name', 'worker-1', 'malaknoyn/clf'])
    time.sleep(600)
    subprocess.call(["docker", "container", 'stop', "worker-1"])


if __name__ == "__main__":
    main()
