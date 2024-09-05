# CAP Composer Web

Running the Wagtail based CAP Composer in a standalone Wagtail site.

This repository contains a sample Docker Compose setup and configuration to include and run
the [CAP Composer](https://github.com/wmo-raf/cap-composer)
in a separate standalone Wagtail site, without necessarily including the
entire [ClimWeb](https://github.com/wmo-raf/nmhs-cms) components.

The [CAP Composer](https://github.com/wmo-raf/cap-composer) is a [Wagtail](https://wagtail.org) based Django package/app
that provides NMHSs a user-friendly interface for creating and managing CAP alerts.

## Prerequisites

Before following the steps below, make sure you have the following set up:

- **Docker Engine & Docker Compose Plugin :** Ensure that Docker Engine is installed and running on the machine where
  you plan to execute the docker-compose command https://docs.docker.com/engine/install/. Docker Engine is the runtime
  environment for containers.

## Installation
<a name="installation-steps"></a>
___

**Warning for Windows users:** To avoid any installation issues, ensure that your default line endings are set to **LF**
in your IDE.

For example, in VS Code you should ensure that the bottom right says 'LF' and *not* 'CRLF'. If you continue to run into
problems, you may consider modifying how Git handles line ending conversion as well (see the `core.autocrlf` section
of [this page](https://git-scm.com/book/en/v2/Customizing-Git-Git-Configuration) for more information).

___

### 1. Clone the Repository

```sh
git clone https://github.com/wmo-raf/cap-composer-web.git
```

### 2. Setup environmental variables

Copy the `.env.sample` file to a `.env` file

```sh
cp .env.sample .env
```

Edit and replace variables appropriately using your text editor. Here is an example using `nano` text editor.

```sh
nano .env
```

See [environmental variables' section](#environmental-variables) below for more details on the required variables

### 3. Create Wagtail static and media directories on the host machine and set correct permissions

Ensure you are using the correct paths as set in the `.env` file for the `CAP_STATIC_VOLUME` and `CAP_MEDIA_VOLUME`
variables.

```sh
mkdir -p ./docker/capsite/static
```

```sh
mkdir -p ./docker/capsite/media
```

#### Update the permissions for the directories

*Note: This step is not necessary on Windows machines.*

```sh
sudo chown <CAP_GID>:<CAP_UID> ./docker/capsite/static
```

```sh
sudo chown <CAP_GID>:<CAP_UID> ./docker/capsite/media
```

Replace `<CAP_GID>` and `<CAP_UID>` with the values set in the `.env` file for the `CAP_GID` and `CAP_UID` variables

### 4. Build and Run the Docker Containers

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

### 5. Create Superuser

```sh
docker-compose exec cap_web python manage.py createsuperuser
```

## Environmental Variables

| Variable Name                | Description                                                                                                                                                                                                        | Required | Default Value           | Details                                                                                                                                                                             |
|:-----------------------------|:-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------|:------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| CAP_UID                      | The id of the `cap` user                                                                                                                                                                                           | Yes      | 1000                    |                                                                                                                                                                                     |
| CAP GID                      | The id of the `cap` group                                                                                                                                                                                          | Yes      | 1000                    |                                                                                                                                                                                     |
| CAP_DB_USER                  | Postgres Database user                                                                                                                                                                                             | Yes      |                         |                                                                                                                                                                                     |
| CAP_DB_NAME                  | Postgres Database name                                                                                                                                                                                             | Yes      |                         |                                                                                                                                                                                     |
| CAP_DB_PASSWORD              | Postgres Database password                                                                                                                                                                                         | Yes      |                         | Avoid using the '@' and '$' or any other special characters without escaping them. If you have to include them, first make sure your password is URL-Encoded to avoid errors        |
| CAP_DB_VOLUME                | Docker Database volume path                                                                                                                                                                                        | Yes      | ./docker/dbdata         |                                                                                                                                                                                     |
| CAP_FERNET_KEY                |                                                            The key used for encryption of MQTT passwords                                                                                                                             | Yes      |          |                                                                                                                                                                 44 character URL-safe string, e.g. ERKBpLzB_P8azusL-CGK-LGZkV8T8edmmN4oYLi0w3Q=                    |
| CAP_DEBUG                    | Django Debug mode                                                                                                                                                                                                  | No       | False                   |                                                                                                                                                                                     |
| CAP_SITE_NAME                | Wagtail Site name                                                                                                                                                                                                  | No       | CAP Composer            |                                                                                                                                                                                     |
| CAP_ADMIN_URL_PATH           | Admin URL path                                                                                                                                                                                                     | No       | cap-admin               |                                                                                                                                                                                     |
| CAP_TIME_ZONE                | A string representing the time zone for this installation.See the [list of time zones](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones). Set this to your country timezone.                           | No       | UTC                     | [List of tz database time zones](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)                                                                                      |
| CAP_SECRET_KEY               | A secret key for a particular Django installation. This is used to provide cryptographic signing, and should be set to a unique, unpredictable value. Django will refuse to start if SECRET_KEY is not set         | Yes      |                         | Avoid the `$` here as well. You can use this online tool [https://djecrety.ir](https://djecrety.ir/) to generate the key and paste. Make sure it does not include the `$` character |
| CAP_ALLOWED_HOSTS            | A list of strings representing the host/domain names that this Django site can serve. This is a security measure to prevent HTTP Host header attacks, which are possible even under many seemingly-safe web server | No       | *                       | [Django Allowed Hosts](https://docs.djangoproject.com/en/4.2/ref/settings/#std-setting-ALLOWED_HOSTS).                                                                              |
| CAP_SMTP_EMAIL_HOST          | Django SMTP email host. Read more about sending Emails on Django [here](https://docs.djangoproject.com/en/5.0/topics/email)                                                                                        | No       |                         |                                                                                                                                                                                     |
| CAP_SMTP_EMAIL_PORT          | Django SMTP email port                                                                                                                                                                                             | No       |                         |                                                                                                                                                                                     |
| CAP_SMTP_EMAIL_USE_TLS       | Django SMTP email use TLS                                                                                                                                                                                          | No       | True                    |                                                                                                                                                                                     |
| CAP_SMTP_EMAIL_HOST_USER     | Django SMTP email host user                                                                                                                                                                                        | No       |                         |                                                                                                                                                                                     |
| CAP_SMTP_EMAIL_HOST_PASSWORD | Django SMTP email host password                                                                                                                                                                                    | No       |                         |                                                                                                                                                                                     |
| CAP_ADMINS                   | Django Admin emails                                                                                                                                                                                                | No       |                         |                                                                                                                                                                                     |
| CAP_DEFAULT_FROM_EMAIL       | Django Default from email                                                                                                                                                                                          | No       |                         |                                                                                                                                                                                     |
| CAP_STATIC_VOLUME            | Docker Static volume path                                                                                                                                                                                          | Yes      | ./docker/capsite/static |                                                                                                                                                                                     |
| CAP_MEDIA_VOLUME             | Docker Media volume path                                                                                                                                                                                           | Yes      | ./docker/capsite/media  |                                                                                                                                                                                     |
| CAP_TLS_VOLUME               | Docker CAP TLS volume path                                                                                                                                                                                         | No       | ./docker/capsite/tls    |                                                                                                                                                                                     |
| CAP_CERT_PATH                | CAP XML Signing Certificate path                                                                                                                                                                                   | No       |                         |                                                                                                                                                                                     |
| CAP_PRIVATE_KEY_PATH         | CAP XML Signing Private key path                                                                                                                                                                                   | No       |                         |                                                                                                                                                                                     |
| CAP_SIGNATURE_METHOD         | CAP XML Signature method                                                                                                                                                                                           | No       | RSA_SHA256              |                                                                                                                                                                                     |
| CAP_GUNICORN_NUM_OF_WORKERS  | Number of Gunicorn workers                                                                                                                                                                                         | No       | 4                       |                                                                                                                                                                                     |
| CAP_GUNICORN_TIMEOUT         | Gunicorn timeout                                                                                                                                                                                                   | No       | 300                     |                                                                                                                                                                                     |
| CAP_NGINX_PORT               | Docker Nginx port                                                                                                                                                                                                  | Yes      | 80                      |                                                                                                                                                                                     |
| CAP_BROKER_USERNAME          | MQTT Broker username                                                                                                                                                                                               | Yes      | cap                     |                                                                                                                                                                                     |
| CAP_BROKER_PASSWORD          | MQTT Broker password                                                                                                                                                                                               | Yes      |                         |                                                                                                                                                                                     |
| CAP_BROKER_QUEUE_MAX         | MQTT Broker queue max                                                                                                                                                                                              | Yes      | 1000                    |                                                                                                                                                                                     |

## Admin Interface

### 1. Access the Wagtail Admin

The admin interface can be accessed at `http://<ip_or_domain>:<CAP_NGINX_PORT>/<CAP_ADMIN_URL_PATH>`.
Replace `<ip_or_domain>` with the IP address or domain name of the site and
`<CAP_NGINX_PORT>` with the port number where the site is running and `<CAP_ADMIN_URL_PATH>` with the admin URL path as
set in the environmental variables.

For example, if the site is running on `http://127.0.0.1:8000` and the admin URL path is set to `cap-admin`, the admin
interface can be accessed at `http://127.0.0.1:8000/cap-admin`.

Below is how the admin interface will look when first accessed.

![Wagtail Admin](docs/images/admin.png)

Login with the superuser credentials created in step 5 above.

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

For the `WMO Register of Alerting Authorities OID`, you go to
the [WMO Register of Alerting Authorities](https://alertingauthority.wmo.int/) site and select your country, then copy
the OID numbers as indicated in the example image below for Kenya Meteorological Service¬.

![WMO Register of Alerting Authorities](docs/images/get_wmo_oid.png)

#### Update Hazard Event Types

This section contains the list of hazard event types that can be used in the CAP alert message. This list should only
include events monitored by the sending authority. You can select from a list of WMO defined event types or add a new
custom one, as monitored by the sending authority. You can select an icon to represent the event type.

![Hazard Event Types](docs/images/update_hazard_types.png)

#### Update Audience Types

This section contains the different audience types that can be used in the CAP alert message. You can create as many
audience types as needed. Usually, you might only need to create one audience type like `General Public` for public
alerts.

![Audience Types](docs/images/update_audience_types.png)

#### Create Predefined Areas

This section contains the predefined areas that can be used in the CAP alert message. The CAP tool allows to create
alert areas using different tools including:

- Drawing a polygon on the map
- Drawing a circle on the map
- Selecting an area from pre-loaded Administrative Boundaries
- Selecting an area from a list of predefined areas

`NOTE:` You can find more details on the functionalities and capabilities of the editor in
the [CAP Composer](https://github.com/wmo-raf/cap-composer) package repository itself.

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

### 6. Signing CAP Alerts

You can provide a certificate and private key to sign the CAP XML alerts. These can be put in the `CAP_TLS_VOLUME`
directory, and named as `cert.pem` and `privkey.pem` respectively. The `CAP_TLS_VOLUME` directory is mounted to
`/app/tls` inside the container.

Then you will need to update the `CAP_CERT_PATH` and `CAP_PRIVATE_KEY_PATH` environment variables to point to absolute
paths of the cert and private key files respectively, as accessible inside the container.

For example, if the cert and private key files are placed on the root of `CAP_TLS_VOLUME` directory, the `CAP_CERT_PATH`
and `CAP_PRIVATE_KEY_PATH` should be set to `/app/tls/cert.pem` and `/app/tls/privkey.pem` respectively.

If you do not have a certificate and private key, you can generate a self-signed certificate and private key using the
following commands, and place them in the `CAP_TLS_VOLUME` directory.

```bash
openssl req -x509 -nodes -subj "/CN=<ip-or-domain>" -days 365 -newkey rsa -keyout privkey.pem -out cert.pem
```

`NOTE:` Make sure to replace `<ip-or-domain>` with the IP address or domain name of the site.

## Development

To test new features, begin by following the <a href="#installation-steps">installation steps</a>.

If any changes are made to the models, the database must also be updated. This can be done as follows:

```bash
docker exec cap_web python manage.py makemigrations
```
*(creates new migration files based on changes to the Django models.)*

```bash
docker exec cap_web python manage.py migrate
```
*(applies the migrations to the database.)*
