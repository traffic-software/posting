import subprocess
import time


def main():
    # docker run --rm -d -it --memory="300m" malaknoyn/clf
    # docker run --rm -d -it --memory="300m" malaknoyn/clf
    # docker run --rm -d -it --memory="300m" malaknoyn/clf
    # docker run --rm -d -it --memory="200m" --env PS_KEY=EAsxrGZ6DY6u --env PS_PROXY_USER=DVxpNeNhZnWmpGib ps_clf
    subprocess.call(["docker", "run", '--rm', "-d", "-it", '--env','PS_KEY=lVQqNJiKQroN','--env','PS_host=supersoft.vip', '--env','PY_FILE_NAME=CLF', '--name', 'worker-1', 'malaknoyn/clf:proxy'])
    # time.sleep(60)
    # subprocess.call(["docker", "run", '--rm', "-d", "-it", '--env','PS_KEY=lVQqNJiKQroN','--env','PS_host=supersoft.vip', '--env','PY_FILE_NAME=CLF', '--name', 'worker-2', 'malaknoyn/clf:proxy'])
    # time.sleep(600)
    # subprocess.call(["docker", "container", 'stop', "worker-1"])
    # time.sleep(60)
    # subprocess.call(["docker", "container", 'stop', "worker-2"])


if __name__ == "__main__":
    main()