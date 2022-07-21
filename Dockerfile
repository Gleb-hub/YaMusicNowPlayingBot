FROM python:3.10

WORKDIR /app

ADD requirements.txt /app

RUN pip install --trusted-host pypi.python.org -r requirements.txt

CMD ["python3.10", "./bot.py"]