## Campus Maintenance and Management System (CMMS)

A desktop database application for managing campus maintenance, renovation, and cleaning. Built with Python (Tkinter) and MySQL, using embedded SQL for all data access.

### Features
- CRUD forms for core entities (people, campus structures, activities, chemicals, companies)
- Set-based (bulk) insert interface for any selected table (CSV/JSON rows)
- SQL query runner with tabular results
- Cleaning schedule search by building(s) and time range with chemical hazard flags
- Reports: workers count by activity type and location type

### Tech
- Python 3.10+
- MySQL 8.0+
- Libraries: `mysql-connector-python`, `tkinter`, `python-dotenv`

### Setup
1) Create a MySQL database (name suggestion: `cmms`).

2) Configure environment variables (create a `.env` file next to the code):
```
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=yourpassword
DB_NAME=cmms
```

3) Install dependencies:
```
pip install -r requirements.txt
```

4) Initialize schema and seed data:
```
mysql -h %DB_HOST% -u %DB_USER% -p%DB_PASSWORD% %DB_NAME% < schema.sql
mysql -h %DB_HOST% -u %DB_USER% -p%DB_PASSWORD% %DB_NAME% < seed.sql
```

5) Run the app:
```
python app.py
```

### Notes
- The CMM administrator uses this app but is not stored as a `Person` record.
- Limits on managers/workers are stored in `Settings` and enforced by the app during inserts/updates.
- Activities can target different campus parts via `(location_type, location_id)` with a helper view `v_activity_location` to display a friendly label.

### Repository hygiene

Course-owned materials, personal contribution records, local virtual environments, Python caches, IDE settings, database credentials, and the large demonstration video are intentionally excluded from this public repository.


