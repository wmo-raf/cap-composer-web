# CAP Composer Web

Running the Wagtail based CAP Composer as a standalone Wagtail site.

## Prerequisites

Before following the steps below, make sure you have the following set up:

- **Docker Engine & Docker Compose Plugin :** Ensure that Docker Engine is installed and running on the machine where
  you plan to execute the docker-compose command https://docs.docker.com/engine/install/. Docker Engine is the runtime
  environment for containers.

## Installation

### 1. Clone the Repository

```sh
git clone https://github.com/wmo-raf/cap-composer-web.git
```

### 2. Setup environmental variables

Prepare a '.env' file with necessary variables from '.env.sample'

```sh
cp .env.sample .env
```

```sh
nano .env
```

### 3. Build and Run the Docker Containers

```sh
docker-compose build
```

```sh
docker-compose up
```

To run the containers in the background, use the `-d` flag

```sh
docker-compose up -d
```

### 4. Create Superuser

```sh
docker-compose exec cap_web python manage.py createsuperuser
```

### 5. Access the Wagtail Admin

The admin interface can be accessed at `http://localhost:{CAP_NGINX_PORT}/{CAP_ADMIN_URL_PATH}`

## Environmental Variables

Edit and replace variables appropriately. See [environmental variables' section](#environmental-variables) below

| Variable Name                | Description                      | Default Value           |
|:-----------------------------|:---------------------------------|:------------------------|
| CAP_DB_USER                  | Postgres Database user           |                         |
| CAP_DB_NAME                  | Postgres Database name           |                         |
| CAP_DB_PASSWORD              | Postgres Database password       |                         |
| CAP_DB_VOLUME                | Docker Database volume path      | ./docker/dbdata         |
| CAP_DEBUG                    | Django Debug mode                | False                   |
| CAP_SITE_NAME                | Wagtail Site name                | CAP Composer            |
| CAP_ADMIN_URL_PATH           | Admin URL path                   | cap-admin               |
| CAP_TIME_ZONE                | Timezone                         | UTC                     |
| CAP_SECRET_KEY               | Django Secret key                |                         |
| CAP_ALLOWED_HOSTS            | Django Allowed hosts             | *                       |
| CAP_SMTP_EMAIL_HOST          | Django SMTP email host           |                         |
| CAP_SMTP_EMAIL_PORT          | Django SMTP email port           |                         |
| CAP_SMTP_EMAIL_USE_TLS       | Django SMTP email use TLS        | True                    |
| CAP_SMTP_EMAIL_HOST_USER     | Django SMTP email host user      |                         |
| CAP_SMTP_EMAIL_HOST_PASSWORD | Django SMTP email host password  |                         |
| CAP_ADMINS                   | Django Admin emails              |                         |
| CAP_DEFAULT_FROM_EMAIL       | Django Default from email        |                         |
| CAP_STATIC_VOLUME            | Docker Static volume path        | ./docker/capsite/static |
| CAP_MEDIA_VOLUME             | Docker Media volume path         | ./docker/capsite/media  |
| CAP_TLS_VOLUME               | Docker CAP TLS volume path       | ./docker/capsite/tls    |
| CAP_CERT_PATH                | CAP XML Signing Certificate path |                         |
| CAP_PRIVATE_KEY_PATH         | CAP XML Signing Private key path |                         |
| CAP_SIGNATURE_METHOD         | CAP XML Signature method         | RSA_SHA256              |
| CAP_GUNICORN_NUM_OF_WORKERS  | Number of Gunicorn workers       | 4                       |
| CAP_GUNICORN_TIMEOUT         | Gunicorn timeout                 | 300                     |
| CAP_NGINX_PORT               | Docker Nginx port                | 80                      |
| CAP_BROKER_USERNAME          | MQTT Broker username             | cap                     |
| CAP_BROKER_PASSWORD          | MQTT Broker password             |                         |
| CAP_BROKER_QUEUE_MAX         | MQTT Broker queue max            | 1000                    |

## Admin Interface

### 1. Access the Wagtail Admin

The admin interface can be accessed at `http://localhost:{CAP_NGINX_PORT}/{CAP_ADMIN_URL_PATH}`. Login with the
superuser credentials created in step 4. Below is how the admin interface will look when first accessed.

![Wagtail Admin](docs/images/admin.png)

### 2. Update Wagtail Site Settings

Navigate to `Settings > Sites` to update the site settings.

![Wagtail Site Settings](docs/images/find_site_settings.png)

Click on the default site (localhost) to edit:

![Wagtail Site Settings](docs/images/update_site_settings.png)

`Hostname`: Should be the IP name or domain name of the site, `without` the protocol (http:// or https://).

`Port`: The port number where the site is running. For http, it is usually 80 and for https, it is usually 443.

`Site Name`: The name of the site.

### 3. Update CAP Base Settings

Before creating a CAP alert page, you will need to update the CAP Base settings. Navigate
to `CAP Alerts > CAP Base Settings`

![CAP Base Settings](docs/images/find_cap_settings.png)

#### Update CAP Sender Details

This section contains the details of the CAP sender. The details are used to populate the `sender` and `contact` element
in the CAP alert message.

![CAP Sender Details](docs/images/update_sender_details.png)

#### Update Hazard Event Types

This section contains the list of hazard event types that can be used in the CAP alert message. This list should only
include events monitored by the sending authority. You can select from a list of WMO defined event types or add a new
custom one as monitored by the sending authority. You can select an icon to represent the event type.

![Hazard Event Types](docs/images/update_hazard_types.png)

#### Update Audience Types

This section contains the different audience types that can be used in the CAP alert message. You can create as many
audie types as needed. Usually, you might only need to create one audience type like `General Public` for public alerts.

![Audience Types](docs/images/update_audience_types.png)

#### Create Predefined Areas

This section contains the predefined areas that can be used in the CAP alert message. The CAP tool allows to create
alert areas using different tools including:

- Drawing a polygon on the map
- Drawing a circle on the map
- Selecting an area from pre-loaded Administrative Boundaries
- Selecting an area from a list of predefined areas

For an area to be selected from predefined areas, it needs to be created here first and saved. You can use the drawing
tools here to trace the predefined areas.

![Predefined Areas](docs/images/update_predefined_areas.png)

### 4. Create a CAP Alert

Navigate to `CAP Alerts > Alerts` to create a new CAP alert. Click on `Add cap alert page` to create a new alert. This
will open a form where you can fill in the details of the alert.

![Create CAP Alert](docs/images/create_cap_alert.png)

### 5. Importing CAP Alerts from external sources

The CAP Composer tool allows you to import CAP alerts published in the standard CAP XML from external sources. To import
CAP alerts, navigate to `CAP Alerts > Import CAP Alert`. You can import CAP alerts from a URL, Copied XML text or from a
file.

![Import CAP Alert](docs/images/import_cap_alert.png)

After loading and previewing the CAP alert, you can create a draft of the alert by clicking on the `Create Draft`
button. This will create a draft of the alert that you can edit and publish.

![Import CAP Alert](docs/images/creat_draft_from_import_alert.png)

