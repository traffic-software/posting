import subprocess
import time


def main():
    # docker run --rm -d -it --memory="300m" malaknoyn/clf
    # docker run --rm -d -it --memory="300m" malaknoyn/clf
    # docker run --rm -d -it --memory="300m" malaknoyn/clf
    # docker run --rm -d -it --memory="200m" --env PS_KEY=EAsxrGZ6DY6u --env PS_PROXY_USER=DVxpNeNhZnWmpGib ps_clf
    subprocess.call(["docker", "run", '--rm', "-d", "-it", "--memory=256m", "--memory-swap=0", "--cpus=0.5", '--env','PS_KEY=EAsxrGZ6DY6u', '--env', 'PS_PROXY_USER=HzoxSzpE1Y_zJf5Y-DVxpNeNhZnWmpGib', '--name', 'worker-1', 'malaknoyn/clf:soax'])
    time.sleep(60)
    subprocess.call(["docker", "run", '--rm', "-d", "-it", "--memory=256m", "--memory-swap=0", "--cpus=0.5", '--env','PS_KEY=EAsxrGZ6DY6u', '--env', 'PS_PROXY_USER=HzoxSzpE1Y_zJf5Y-DVxpNeNhZnWmpGib', '--name', 'worker-2', 'malaknoyn/clf:soax'])
    time.sleep(600)
    subprocess.call(["docker", "container", 'stop', "worker-1"])
    time.sleep(60)
    subprocess.call(["docker", "container", 'stop', "worker-2"])


if __name__ == "__main__":
    main()
