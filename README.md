# Jasmin-web-gui: Joyce
Tired of the jcli, you are not sure how to get things quickly running in [Jasmin](https://docs.jasminsms.com/), well take a deep breathe and thank God I had some free time on my hands.

[Jasmin](https://docs.jasminsms.com/) allows you to programmatically manage groups, users routers, connectors, etc. using its [Perspective broker API](https://docs.jasminsms.com/en/latest/faq/developers.html) 
In this project we are not "teleneting" our way to jcli, we are abandoning it entirely in favor of the [Perspective broker API](https://docs.jasminsms.com/en/latest/faq/developers.html).

Joyce is a simple [Django](http://www.djangoproject.com) application that  helps you interface and configure different Jasmin components to get your SMSs out on the way as fast as possible.
**NOTE:** We have prepared all the components you need as docker images so you do not have to worry about how to get everything spinning, just take a 14min docker tutorial and you are ready to go.

The steps in this document assume that you have some at least some programming experience. but fear not, if you are not a developer.
We also have a script you can just run to get everything up for you. We want you to start sending SMS via Jasim as fast as you want.

## Local development
In the setup below, makesure you have jasmin installed and running on your machine.
If you do not want hustle with installing Jasmin manually see (docker images)

This is a minimal Django 5.0 project. 

### Using  pip 
1. Create a virtualenv
    `python3.11 -m venv venv` // whichever way you always create this
2. Activate the virtualenv
    `source venv/bin/activate`
3. Install the dependencies using pip
4. `pip install -r requirements.txt`
