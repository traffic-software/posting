import subprocess
import time
import os
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
# print(dname)
# print(abspath)
# print(' '.join(["docker", "run", '--rm', "-d", "-it", '-v', "{0}:/data".format(dname),  '--env', 'PS_KEY=cAHd0tNSTN4H',
# '--env', 'PS_HOST=post.pointssoft.com', '--name', 'worker-1', 'ultrafunk/undetected-chromedriver', 'ipython', 'data/GCW.py']))


def main():
    # docker run --rm -d -it --memory="300m" malaknoyn/clf
    # docker run --rm -d -it --memory="300m" malaknoyn/clf
    # docker run --rm -d -it --memory="300m" malaknoyn/clf
    # docker run --rm -d -it  --env PS_KEY=cAHd0tNSTN4H --env PS_HOST=post.pointsoft.com pkey
    # find . ! -iregex ".*\.php.*" -exec cp {} /destination/folder/ \;
    # find -iname "22*.png" -exec cp {} /r/ \;
    # find -iname "22*.png" -exec cp {};
    # docker run --rm -it -v ${PWD}:/data  --env PS_KEY=cAHd0tNSTN4H --env PS_HOST=post.pointssoft.com  ultrafunk/undetected-chromedriver ipython data/GCW.py
    subprocess.call(["docker", "container", 'stop', "worker-1"])
    time.sleep(60)
    subprocess.call(["docker", "run", '--rm', "-d", "-it", '-v', "{0}:/data".format(dname),  '--env', 'PS_KEY=ONeR6BXX5Xbu',
                    '--env', 'PS_HOST=post.pointssoft.com', '--name', 'worker-1', 'ultrafunk/undetected-chromedriver', 'ipython', 'data/GCW.py'])


if __name__ == "__main__":
    main()
    # pass
