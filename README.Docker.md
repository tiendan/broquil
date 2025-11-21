# Docker Setup Guide

This guide will help you run the Broquil application using Docker with MySQL database and Adminer for database management.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) installed
- [Docker Compose](https://docs.docker.com/compose/install/) installed
- [Poe](https://poethepoet.natn.io/) task runner: `pip install poethepoet`

## Quick Start

### 1. Initial Setup

Create your environment file from the example:

```bash
cp .env.example .env
```

Edit `.env` and update the values (especially passwords and secret key):

```env
MYSQL_DATABASE=broquil
MYSQL_USER=broquil_user
MYSQL_PASSWORD=your_secure_password_here
MYSQL_ROOT_PASSWORD=your_secure_root_password_here
DJANGO_SECRET_KEY=your-secret-key-here-generate-a-long-random-string
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
DATABASE_ENGINE=mysql
```

### 2. Start the Application

Run the setup task (this will create .env, build containers, and run migrations):

```bash
poe setup
```

Or manually:

```bash
poe start-dev
```

This will start three services:
- **Web application**: http://localhost:8000
- **MySQL database**: localhost:3307
- **Adminer (DB admin)**: http://localhost:8080

### 3. Create a Superuser

```bash
poe createsuperuser
```

### 4. Access the Application

- **Application**: http://localhost:8000
- **Admin Panel**: http://localhost:8000/admin/
- **Adminer**: http://localhost:8080

## Common Tasks (Poe Commands)

### Service Management

```bash
# Start services (build and run in background)
poe start-dev

# Stop services
poe stop-dev

# Restart web service
poe restart-dev

# View logs
poe logs

# Check running services
poe ps

# Clean everything (WARNING: destroys data!)
poe clean
```

### Django Management

```bash
# Run migrations
poe migrate

# Create new migrations
poe makemigrations

# Open Django shell
poe shell

# Create superuser
poe createsuperuser

# Collect static files
poe collectstatic

# Run tests
poe test

# Check for Django issues
poe check
```

### Database Management

```bash
# Open MySQL shell
poe db-shell

# Reset database (WARNING: destroys all data!)
poe db-reset
```

### Utilities

```bash
# Open bash shell in web container
poe bash
```

## Importing Production Data

### Using Adminer (Recommended)

1. Access Adminer at http://localhost:8080
2. Login with these credentials:
   - **System**: MySQL
   - **Server**: db
   - **Username**: broquil_user (or value from your .env)
   - **Password**: broquil_pass (or value from your .env)
   - **Database**: broquil (or value from your .env)
3. Click "Import" in the left menu
4. Select your SQL dump file
5. Click "Execute"

### Using Command Line

```bash
# Export from production
mysqldump -u username -p database_name > backup.sql

# Import to Docker MySQL
docker-compose exec -T db mysql -u broquil_user -p broquil < backup.sql
```

## Development Workflow

1. **Code changes**: Files are mounted as volumes, so changes are reflected immediately
2. **Database changes**: Run `poe makemigrations` and `poe migrate`
3. **View logs**: Run `poe logs` to see application output
4. **Debug**: Access Django shell with `poe shell` or bash with `poe bash`

## Switching Between SQLite and MySQL

The application supports both databases via environment variables:

### Use MySQL (Docker)
```env
DATABASE_ENGINE=mysql
```

### Use SQLite (local file)
```env
DATABASE_ENGINE=sqlite
```

Or simply unset `DATABASE_ENGINE` to default to SQLite.

## Troubleshooting

### Database connection refused

Wait a few seconds for MySQL to fully start, then try again:

```bash
poe stop-dev
poe start-dev
```

### Permission errors

The application runs as a non-root user (UID 1000). If you get permission errors:

```bash
sudo chown -R 1000:1000 .
```

### Port conflicts

If ports 8000, 8080, or 3307 are already in use, edit `docker-compose.yaml` to use different ports.

### Fresh start

To completely reset everything:

```bash
poe clean
poe setup
```

## Time Manipulation for Testing

The Docker container includes `libfaketime` which allows you to run your application with a fake system time for testing purposes.

### Using Fake Time with Poe Tasks

**Run Django shell with fake time:**
```bash
# Use relative dates
FAKETIME="last wednesday" poe faketime
FAKETIME="2 days ago" poe faketime
FAKETIME="next friday" poe faketime

# Use specific dates (note: time must include seconds HH:MM:SS)
FAKETIME="2024-11-13 10:30:00" poe faketime
FAKETIME="2024-01-01 00:00:00" poe faketime

# Or just date (defaults to 00:00:00)
FAKETIME="2024-11-13" poe faketime
```

**Run development server with fake time:**
```bash
FAKETIME="2024-11-13 14:30:00" poe runserver-faketime
# Access at http://localhost:8000 - the app will think it's Nov 13, 2024 at 2:30 PM
```

**Execute any command with fake time:**
```bash
# Run migrations with fake time
FAKETIME="2024-11-13 10:00:00" CMD="python manage.py migrate" poe exec-faketime

# Run tests with fake time
FAKETIME="last monday" CMD="python manage.py test" poe exec-faketime
```

### Using Fake Time Directly with docker-compose

```bash
# Run any docker-compose command with fake time
# Note: time format must include seconds (HH:MM:SS)
docker-compose run --rm \
  -e LD_PRELOAD=/usr/lib/aarch64-linux-gnu/faketime/libfaketime.so.1 \
  -e FAKETIME="2024-11-13 14:30:00" \
  web python manage.py shell

# For x86_64 systems, use:
# -e LD_PRELOAD=/usr/lib/x86_64-linux-gnu/faketime/libfaketime.so.1
```

### Supported Date Formats

libfaketime supports many date formats:
- **Relative**: `"last wednesday"`, `"2 days ago"`, `"next friday"`
- **Date only**: `"2024-11-13"` (defaults to 00:00:00)
- **Date + time**: `"2024-11-13 14:30:00"` (⚠️ **must include seconds**: HH:MM:SS)
- **Timestamps**: `"@1699876800"` (Unix timestamp)
- **Offset**: `"+5d"` (5 days in the future), `"-2h"` (2 hours ago)

> **Important**: When specifying time, always use the full format `HH:MM:SS`. Using `HH:MM` will cause an error.

### Examples

```bash
# Test weekly report generation as if it's last Wednesday
FAKETIME="last wednesday" poe faketime
>>> from myapp.reports import generate_weekly_report
>>> generate_weekly_report()  # Runs with last Wednesday's date

# Test order processing for a specific date and time
FAKETIME="2024-11-13 10:00:00" poe faketime
>>> from elbroquil.models import Order
>>> from django.utils import timezone
>>> Order.objects.filter(created_at__date=timezone.now().date())
```

## Production Deployment

For production:

1. Update `.env` with production values
2. Set `DEBUG=False`
3. Set proper `ALLOWED_HOSTS`
4. Use a strong `DJANGO_SECRET_KEY`
5. Use strong database passwords
6. Consider using `docker-compose.override.yml` for production-specific settings
7. Use a production WSGI server (Gunicorn is already in requirements.txt)

## Support

For issues, check the logs:

```bash
poe logs
```

Or access the container directly:

```bash
poe bash
```
