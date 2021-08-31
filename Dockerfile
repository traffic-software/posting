FROM selenium/standalone-chrome
# FROM dorowu/ubuntu-desktop-lxde-vnc
USER root
RUN apt-get update -y
RUN apt-get install sudo -y
RUN apt-get install nano -y
RUN apt-get install python3 -y
RUN sudo apt install python3-pip -y
RUN sudo apt-get install openssh-server -y
RUN sudo apt-get install -y supervisor
RUN python3 -m pip install selenium
RUN python3 -m pip install requests
RUN python3 -m pip install zipfile38
RUN python3 -m pip install imapclient
RUN python3 -m pip install python_anticaptcha
RUN python3 -m pip install chardet
RUN python3 -m pip install PyEmailTools
RUN python3 -m pip install pyvirtualdisplay
RUN python3 -m pip install fake-useragent

RUN apt-get install -y net-tools 
ADD . /mydir/
ADD supervisord.conf /etc/supervisor/conf.d/supervisord.conf


RUN sudo systemctl enable ssh
RUN useradd -rm -d /home -s /bin/bash -g root -G sudo -u 1000 test
RUN  echo 'test:test' | chpasswd
RUN sudo service ssh start
# RUN sudo service supervisor start
EXPOSE 22
# RUN /bin/sh -c '/usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf'
# CMD ["/usr/bin/supervisord","-c","/etc/supervisor/conf.d/supervisord.conf"]
#whereis python 
#{ crontab -l; echo "* * * * * /usr/bin/python3 /mydir/smtp.py"; } | crontab -
# docker build . -t selenium-chrome && \
# docker run -it selenium-chrome python3
#docker save -o au.tar au
# docker load -i au.tar
#docker  run -e HTTP_PROXY=http://malaknoyn:4mdloQgXxS8lcB3J@proxy.packetstream.io:31112 -e HTTPS_PROXY=http://malaknoyn:4mdloQgXxS8lcB3J@proxy.packetstream.io:31112 au