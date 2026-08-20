-- CMMS Database Schema (MySQL) - New Schema
-- All names in English; follows consistent naming conventions

-- Drop existing views first
DROP VIEW IF EXISTS v_activity_core;
DROP VIEW IF EXISTS v_activity_location;

-- Drop existing tables for a clean setup (order respects FKs)
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS ActivityChemical;
DROP TABLE IF EXISTS Contract;
DROP TABLE IF EXISTS Assignment;
DROP TABLE IF EXISTS Activity;
DROP TABLE IF EXISTS Supervision;
DROP TABLE IF EXISTS Chemical;
DROP TABLE IF EXISTS Contractor;
DROP TABLE IF EXISTS Room;
DROP TABLE IF EXISTS Level;
DROP TABLE IF EXISTS Building;
DROP TABLE IF EXISTS Employee;
DROP TABLE IF EXISTS Config;
SET FOREIGN_KEY_CHECKS = 1;

-- Config table for system settings
CREATE TABLE Config (
  config_key VARCHAR(100) PRIMARY KEY,
  config_value VARCHAR(255)
);

-- Employee table
CREATE TABLE Employee (
  emp_id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(150) UNIQUE,
  role ENUM('EXECUTIVE','MANAGER','WORKER') NOT NULL,
  phone VARCHAR(40),
  manager_id INT NULL,
  hire_date DATE,
  status VARCHAR(50),
  CONSTRAINT fk_employee_manager FOREIGN KEY (manager_id) REFERENCES Employee(emp_id) ON DELETE SET NULL
);

-- Building table
CREATE TABLE Building (
  building_id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL UNIQUE,
  address VARCHAR(255),
  description TEXT
);

-- Level table
CREATE TABLE Level (
  level_id INT AUTO_INCREMENT PRIMARY KEY,
  building_id INT NOT NULL,
  level_no INT NOT NULL,
  description VARCHAR(255),
  CONSTRAINT fk_level_building FOREIGN KEY (building_id) REFERENCES Building(building_id) ON DELETE CASCADE,
  UNIQUE (building_id, level_no)
);

-- Room table (weak entity with composite primary key)
CREATE TABLE Room (
  level_id INT NOT NULL,
  room_no VARCHAR(20) NOT NULL,
  capacity INT,
  `usage` VARCHAR(100),
  PRIMARY KEY (level_id, room_no),
  CONSTRAINT fk_room_level FOREIGN KEY (level_id) REFERENCES Level(level_id) ON DELETE CASCADE
);

-- Activity table
CREATE TABLE Activity (
  activity_id INT AUTO_INCREMENT PRIMARY KEY,
  `type` ENUM('CLEANING','MAINTENANCE','RENOVATION','EMERGENCY') NOT NULL,
  description TEXT,
  scheduled_start TIMESTAMP NOT NULL,
  scheduled_end TIMESTAMP NOT NULL,
  status ENUM('SCHEDULED','ONGOING','COMPLETED','CANCELLED') NOT NULL DEFAULT 'SCHEDULED',
  priority INT DEFAULT 0,
  created_by INT,
  location_building_id INT NULL,
  location_level_id INT NULL,
  location_room_no VARCHAR(20) NULL,
  is_outsourced BOOLEAN DEFAULT FALSE,
  CONSTRAINT fk_activity_created_by FOREIGN KEY (created_by) REFERENCES Employee(emp_id) ON DELETE SET NULL,
  CONSTRAINT fk_activity_building FOREIGN KEY (location_building_id) REFERENCES Building(building_id) ON DELETE SET NULL,
  CONSTRAINT fk_activity_level FOREIGN KEY (location_level_id) REFERENCES Level(level_id) ON DELETE SET NULL,
  CONSTRAINT chk_activity_time_order CHECK (scheduled_end > scheduled_start)
  -- Note: Location validation rules (enforced at application level):
  -- - If location_room_no IS NOT NULL, then location_level_id and location_building_id must also be NOT NULL
  -- - If location_level_id IS NOT NULL, then location_building_id must also be NOT NULL
  -- - All three location fields can be NULL (no location specified)
);

-- Assignment table
CREATE TABLE Assignment (
  activity_id INT NOT NULL,
  emp_id INT NOT NULL,
  assigned_role VARCHAR(50),
  hours_assigned DECIMAL(10,2),
  status VARCHAR(50),
  PRIMARY KEY (activity_id, emp_id),
  CONSTRAINT fk_assignment_activity FOREIGN KEY (activity_id) REFERENCES Activity(activity_id) ON DELETE CASCADE,
  CONSTRAINT fk_assignment_employee FOREIGN KEY (emp_id) REFERENCES Employee(emp_id) ON DELETE CASCADE
);

-- Chemical table
CREATE TABLE Chemical (
  chemical_id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(120) NOT NULL UNIQUE,
  hazard_class VARCHAR(50),
  safety_notes TEXT
);

-- ActivityChemical table
CREATE TABLE ActivityChemical (
  activity_id INT NOT NULL,
  chemical_id INT NOT NULL,
  quantity DECIMAL(10,2),
  PRIMARY KEY (activity_id, chemical_id),
  CONSTRAINT fk_ac_activity FOREIGN KEY (activity_id) REFERENCES Activity(activity_id) ON DELETE CASCADE,
  CONSTRAINT fk_ac_chemical FOREIGN KEY (chemical_id) REFERENCES Chemical(chemical_id) ON DELETE CASCADE
);

-- Contractor table
CREATE TABLE Contractor (
  contractor_id INT AUTO_INCREMENT PRIMARY KEY,
  company_name VARCHAR(120) NOT NULL UNIQUE,
  contact_person VARCHAR(100),
  contact_phone VARCHAR(40),
  contract_terms TEXT
);

-- Contract table
CREATE TABLE Contract (
  activity_id INT PRIMARY KEY,
  contractor_id INT NOT NULL,
  contract_start DATE,
  contract_end DATE,
  cost DECIMAL(15,2),
  CONSTRAINT fk_contract_activity FOREIGN KEY (activity_id) REFERENCES Activity(activity_id) ON DELETE CASCADE,
  CONSTRAINT fk_contract_contractor FOREIGN KEY (contractor_id) REFERENCES Contractor(contractor_id) ON DELETE CASCADE
);

-- Supervision table
CREATE TABLE Supervision (
  manager_emp_id INT NOT NULL,
  building_id INT NOT NULL,
  since_date DATE,
  PRIMARY KEY (manager_emp_id, building_id),
  CONSTRAINT fk_supervision_manager FOREIGN KEY (manager_emp_id) REFERENCES Employee(emp_id) ON DELETE CASCADE,
  CONSTRAINT fk_supervision_building FOREIGN KEY (building_id) REFERENCES Building(building_id) ON DELETE CASCADE
);

-- View to help resolve activity location text
CREATE OR REPLACE VIEW v_activity_location AS
SELECT a.activity_id,
       a.location_building_id,
       a.location_level_id,
       a.location_room_no,
       CASE
         WHEN a.location_room_no IS NOT NULL AND a.location_level_id IS NOT NULL THEN
           CONCAT(COALESCE(b.name, ''), ' L', COALESCE(l.level_no, ''), ' R', a.location_room_no)
         WHEN a.location_level_id IS NOT NULL THEN
           CONCAT(COALESCE(b.name, ''), ' L', COALESCE(l.level_no, ''))
         WHEN a.location_building_id IS NOT NULL THEN
           COALESCE(b.name, 'Unknown Building')
         ELSE 'No Location'
       END AS location_label
FROM Activity a
LEFT JOIN Building b ON b.building_id = a.location_building_id
LEFT JOIN Level l ON l.level_id = a.location_level_id;

-- Helpful view for reports
CREATE OR REPLACE VIEW v_activity_core AS
SELECT a.activity_id,
       a.`type`,
       a.scheduled_start,
       a.scheduled_end,
       a.status,
       a.priority,
       v.location_label
FROM Activity a
LEFT JOIN v_activity_location v ON v.activity_id = a.activity_id;
