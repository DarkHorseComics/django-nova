django-nova
===========
Django Nova is a simple newsletter manager for Django.

Features
--------
- Double opt-in
- Multiple newsletters per site
- Template driven email generation
- Built-in click tracking with Google Analytics
- Supports [Premailer](https://github.com/alexdunae/premailer/) out of the box
- Full test suite

Requirements
------------
- Django 1.2
- BeautifulSoup
- Mock
- [django-html5](https://github.com/rhec/django-html5) (todo: remove dependency)
- [Finch](https://bitbucket.org/rcoder/finch/overview) (optional)
- [Premailer](https://github.com/alexdunae/premailer/) (optional)

Usage
-----
Once installed you can begin creating newsletters and newsletter issues
(individual mailings) via the Django admin.

Installation
------------
Install django-nova in your site-packages directory:

    # From GitHub
    pip install git+git://github.com/DarkHorseComics/django-nova.git#egg=DjangoNova

    # From BitBucket
    pip install https://bitbucket.org/darkhorse/django-nova

Add django-nova to your installed apps in settings.py:

    INSTALLED_APPS = (
        # ...
        'nova',
    )

Include the nova.urls in your urls.py:

    urlpatterns = patterns('',
        (r'^nova/', include('nova.urls')),
    )

Configuration
-------------
Nova has a variety of settings.py variables that you can use to change
the default behavior.

    # Default email used when sending newsletters
    NOVA_FROM_EMAIL = 'dhdigital@darkhorse.com'

    # If you have not installed premailer set this to False
    NOVA_USE_PREMAILER = True

    # A list of processors to use when adding context to the newsletter template
    NOVA_CONTEXT_PROCESSORS = ('foo.bar.def',)

Template Integration
--------------------
Default newsletter templates can be added to your project's `template` folder and
referenced when adding or updating a newsletter object in the Django admin. These
tempaltes are loaded using any registered template loaders.

Contributing
------------
Please feel free to fork the repository and create a pull request to have your
changes merged back in.

Don't hesitate to contact us if you need help.
