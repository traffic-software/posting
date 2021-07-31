# FROM selenium/standalone-chrome
FROM debian:latest
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
#whereis chromedriver

# docker build . -t selenium-chrome && \
# docker run -it selenium-chrome python3
#https://tecadmin.net/setup-selenium-with-chromedriver-on-debian/