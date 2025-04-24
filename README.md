# ☕ Joyce: Django GUI for Jasmin SMS Gateway

Tired of fiddling with `jcli`? Joyce is a friendly Django interface that lets you manage Jasmin SMS Gateway using its powerful Perspective Broker API. Send SMS, create groups, add users, and more — all through a clean UI.

---

## 🎯 Purpose

[Jasmin](https://docs.jasminsms.com/) allows managing SMS routing via CLI (`jcli`) or the more developer-friendly [Perspective Broker API](https://docs.jasminsms.com/en/latest/faq/developers.html). Joyce uses the PB API to offer:

- Group management
- User management
- Route configuration
- And more...
- No more `telnet`, no more `jcli`

---

## 🔌 Integration with Jasmin

This Django application uses the Twisted framework to communicate with the Jasmin RouterPB service.

The integration relies on a custom service layer that uses Twisted’s asynchronous Perspective Broker client to interact with the running Jasmin service.


## 🛠 Setup Guide

This project uses [Poetry](https://python-poetry.org) for dependency management and includes Docker support for consistent local environments.

### Requirements

- Python 3.11+
- Poetry
- Docker (optional but recommended)
- Jasmin SMS Gateway (via Docker or manual installation)

### Step-by-step (Local)

1. Clone the project:
    ```bash
   git clone https://github.com/ekeeya/jasmin-web-gui.git 
    ```
   ```bash
   cd jasmin-web-gui
    ```

2. Create and activate virtual environment:
    ```bash
   python3.11 -m venv venv
   ```
   ```bash
   source venv/bin/activate
   ```
   Optionally install poetry in the ven if you do not have it globally using pip
   ```bash
   pip install poerty
   ```

3. Install dependencies:
    ```bash
   poetry install
   ```

4. Apply migrations:
   ```bash
   python manage.py migrate
    ```

5. Start server:
   ```bash
   python manage.py runserver
   ```

---

## 🐳 Running Services Docker  

We recommend using Docker for local dev environments. The full Docker setup is defined in `docker-compose.yml`.
In production you may want to add your django service to `docker-compose.yml` but in dev, you may want to run the django project in an IDE that allows debugging.
That is why we have excluded (commented it out by default)

### 📦 What's Included

This project is a complete, containerized environment for Jasmin and supporting services:

- A Django web GUI for Jasmin (disabled in docker by default as explained above )
- Redis (for caching and Celery results)
- RabbitMQ (as Celery broker)
- Jasmin SMS Gateway
- Jasmin REST API container (served via twistd + WSGI)
- A test SMPP server (`smppsim`) for development

To bring up the services:

   ```bash
   docker compose up --build
   ```

---

## 🤝 Contributing

If you find this useful, feel free to fork, improve, and submit pull requests. Bug reports and feature suggestions are always welcome.

---

## ❤️ Thanks

Thanks to the amazing [Jasmin team](https://www.jasminsms.com/) for building such a powerful and extensible SMS gateway. This project is made possible because of their work.

---

## ☕ Buy Me a Coffee on Crypto

If this project helped you avoid hours of pain, consider showing some love, unfortunately we only have crypto:

**BTC Wallet:** `13it3P99sbMrtobij7S9ecJbE6jTciUw7E`

**ETH Wallet:** `0xA83a39024BEd22ebcE2e64c8D28b541140A9d18d`

Every sip counts and boosts moral!

---


## 📬 Contact

Want to get in touch?

- **Email:** ekeeya@ds.co.ug
- **Phone:** +256 765 810-344  
- **X:** [@keldoticom](https://x.com/keldoticom)

For business inquiries, feel free to reach out any time.
