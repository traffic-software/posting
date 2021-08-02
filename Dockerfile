FROM selenium/standalone-chrome


USER root
RUN apt-get update -y
RUN apt-get install sudo -y
RUN apt-get install python3 -y
RUN sudo apt install python3-pip -y
RUN python3 -m pip install selenium
RUN python3 -m pip install requests
RUN python3 -m pip install zipfile38
RUN python3 -m pip install imapclient
RUN python3 -m pip install python_anticaptcha
RUN python3 -m pip install chardet
RUN python3 -m pip install PyEmailTools
ADD . /mydir/

RUN sudo apt-get install openssh-server -y
RUN sudo systemctl enable ssh


RUN useradd -rm -d /home -s /bin/bash -g root -G sudo -u 1000 test
RUN  echo 'test:test' | chpasswd
RUN sudo service ssh start
EXPOSE 22
CMD ["/usr/sbin/sshd","-D"]
#whereis chromedriver

# docker build . -t selenium-chrome && \
# docker run -it selenium-chrome python3