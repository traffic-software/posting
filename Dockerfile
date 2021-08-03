# FROM selenium/standalone-chrome
FROM debian:latest
USER root
RUN apt-get update -y
RUN apt-get install sudo -y
RUN apt-get install python3 -y
RUN sudo apt install python3-pip -y
RUN python3 -m pip install requests
RUN python3 -m pip install zipfile38
RUN python3 -m pip install imapclient
RUN python3 -m pip install python_anticaptcha
RUN python3 -m pip install chardet
RUN python3 -m pip install PyEmailTools -y
RUN sudo apt-get install wget -y
RUN sudo apt-get install unzip -y
ADD . /home/
RUN sudo apt-get install openssh-server -y
RUN sudo systemctl enable ssh


RUN useradd -rm -d /home/test -s /bin/bash -g root -G sudo -u 1000 test
RUN  echo 'test:test' | chpasswd
RUN sudo service ssh start
EXPOSE 22
CMD ["/usr/sbin/sshd","-D"]
#whereis google-chrome-stable
#whereis google-chrome
#whereis chromedriver

# docker build . -t psdebian && \
# docker run -it selenium-chrome python3
#https://tecadmin.net/setup-selenium-with-chromedriver-on-debian/
# docker run  -dit --network ps-macvlan-net -p 22:22 --ip=192.168.0.112 --name py-vlan1 psdebian



#List: docker images -a
#Remove: docker rmi $(docker images -a -q)
#python3 bakecaincontrii.py