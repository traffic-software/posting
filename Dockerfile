FROM selenium/standalone-chrome
# FROM dorowu/ubuntu-desktop-lxde-vnc
USER root
RUN apt-get update -y
RUN apt-get install sudo -y
#crontab install
# RUN apt-get -y install cron
# RUN touch /var/log/cron.log
# RUN (crontab -l ; echo "* * * * * cd ~ && cd /mydir && /usr/bin/python3 reply.py >> /var/log/cron.log") | crontab
# RUN service cron restart


# ssh server setup 
RUN sudo apt-get install openssh-server -y
RUN sudo systemctl enable ssh
RUN useradd -rm -d /home -s /bin/bash -g root -G sudo -u 1000 test
RUN  echo 'test:test' | chpasswd
EXPOSE 22
RUN service ssh start
#install text editor
RUN apt-get install nano -y
#install python and python module
RUN apt-get install python3 -y
RUN sudo apt install python3-pip -y
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
# prossess meneger

RUN sudo apt-get install -y supervisor
RUN touch /mydir/worker.log
ADD supervisord.conf /etc/supervisor/conf.d/supervisord.conf

CMD ["/usr/bin/supervisord","-c","/etc/supervisor/conf.d/supervisord.conf"]







# CMD cron && tail -f /var/log/cron.log
# RUN /bin/sh -c '/usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf'
# CMD ["/usr/bin/supervisord","-c","/etc/supervisor/conf.d/supervisord.conf"]
#whereis python 
#{ crontab -l; echo "* * * * * /usr/bin/python3 /mydir/smtp.py"; } | crontab -
# docker build . -t selenium-chrome && \
# docker run -it selenium-chrome python3
#docker save -o au.tar au
# docker load -i au.tar
#docker  run -e HTTP_PROXY=http://malaknoyn:4mdloQgXxS8lcB3J@proxy.packetstream.io:31112 -e HTTPS_PROXY=http://malaknoyn:4mdloQgXxS8lcB3J@proxy.packetstream.io:31112 au