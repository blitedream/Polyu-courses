-- Seed data for CMMS - New Schema

-- Config settings
INSERT INTO Config (config_key, config_value) VALUES
('max_managers', '10'),
('max_workers', '100')
ON DUPLICATE KEY UPDATE config_value=VALUES(config_value);

-- Employees
-- First insert Alice (EXECUTIVE) without manager
INSERT INTO Employee (name, email, role, phone, manager_id, hire_date, status) VALUES
('Alice Chan', 'alice.chan@example.edu', 'EXECUTIVE', '+852 5555 0001', NULL, '2020-01-15', 'ACTIVE');

-- Then insert managers with reference to Alice
INSERT INTO Employee (name, email, role, phone, manager_id, hire_date, status)
SELECT 'Bob Wong', 'bob.wong@example.edu', 'MANAGER', '+852 5555 0002', 
       (SELECT emp_id FROM Employee WHERE name='Alice Chan' LIMIT 1), 
       '2020-03-01', 'ACTIVE'
WHERE NOT EXISTS (SELECT 1 FROM Employee WHERE name='Bob Wong');

INSERT INTO Employee (name, email, role, phone, manager_id, hire_date, status)
SELECT 'Carol Lee', 'carol.lee@example.edu', 'MANAGER', '+852 5555 0003',
       (SELECT emp_id FROM Employee WHERE name='Alice Chan' LIMIT 1),
       '2020-03-15', 'ACTIVE'
WHERE NOT EXISTS (SELECT 1 FROM Employee WHERE name='Carol Lee');

-- Then insert workers with reference to Bob
INSERT INTO Employee (name, email, role, phone, manager_id, hire_date, status)
SELECT 'David Ng', 'david.ng@example.edu', 'WORKER', '+852 5555 0004',
       (SELECT emp_id FROM Employee WHERE name='Bob Wong' LIMIT 1),
       '2021-01-10', 'ACTIVE'
WHERE NOT EXISTS (SELECT 1 FROM Employee WHERE name='David Ng');

INSERT INTO Employee (name, email, role, phone, manager_id, hire_date, status)
SELECT 'Eva Ho', 'eva.ho@example.edu', 'WORKER', '+852 5555 0005',
       (SELECT emp_id FROM Employee WHERE name='Bob Wong' LIMIT 1),
       '2021-02-20', 'ACTIVE'
WHERE NOT EXISTS (SELECT 1 FROM Employee WHERE name='Eva Ho');

-- Buildings
INSERT INTO Building (name, address, description) VALUES
('Block A', '123 Main Street', 'Main academic building with classrooms and offices'),
('Block B', '456 Second Avenue', 'Secondary building with labs and workshops')
ON DUPLICATE KEY UPDATE name=VALUES(name);

-- Levels
INSERT INTO Level (building_id, level_no, description)
SELECT b.building_id, n, CONCAT('Level ', n) FROM Building b 
JOIN (SELECT 1 AS n UNION SELECT 2 UNION SELECT 3) nums
WHERE b.name = 'Block A'
ON DUPLICATE KEY UPDATE description=VALUES(description);

INSERT INTO Level (building_id, level_no, description)
SELECT b.building_id, n, CONCAT('Level ', n) FROM Building b 
JOIN (SELECT 1 AS n UNION SELECT 2) nums
WHERE b.name = 'Block B'
ON DUPLICATE KEY UPDATE description=VALUES(description);

-- Rooms for Block A Level 1 and Level 2
INSERT INTO Room (level_id, room_no, capacity, `usage`)
SELECT l.level_id, rn, 30, 'Classroom' FROM Level l
JOIN (SELECT '101' rn UNION SELECT '102' UNION SELECT '201' UNION SELECT '202') r
WHERE l.level_no IN (1,2) AND l.building_id = (SELECT building_id FROM Building WHERE name='Block A' LIMIT 1)
ON DUPLICATE KEY UPDATE capacity=VALUES(capacity), `usage`=VALUES(`usage`);

-- Chemicals
INSERT INTO Chemical (name, hazard_class, safety_notes) VALUES
('Ammonia Cleaner', 'MEDIUM', 'Use in well-ventilated areas. Avoid contact with eyes.'),
('Chlorine Bleach', 'HIGH', 'Highly corrosive. Do not mix with ammonia. Use protective equipment.'),
('Eco Floor Soap', 'LOW', 'Environmentally friendly. Safe for regular use.')
ON DUPLICATE KEY UPDATE hazard_class=VALUES(hazard_class), safety_notes=VALUES(safety_notes);

-- Contractors
INSERT INTO Contractor (company_name, contact_person, contact_phone, contract_terms) VALUES
('BrightFix Ltd', 'John Smith', '+852 5555 1111', 'Standard maintenance contract. 24/7 emergency service available.'),
('CleanPro Services', 'Mary Johnson', '+852 5555 2222', 'Monthly cleaning service. Includes all supplies and equipment.')
ON DUPLICATE KEY UPDATE contact_person=VALUES(contact_person), contact_phone=VALUES(contact_phone), contract_terms=VALUES(contract_terms);

-- Managers supervise buildings
INSERT INTO Supervision (manager_emp_id, building_id, since_date)
SELECT p.emp_id, b.building_id, '2020-03-01' FROM Employee p, Building b
WHERE p.name = 'Bob Wong' AND b.name IN ('Block A','Block B')
ON DUPLICATE KEY UPDATE since_date=VALUES(since_date);

-- Sample activities
-- Cleaning in Block A Room 101 tomorrow 9-11, uses chemicals
INSERT INTO Activity (
  `type`, description, scheduled_start, scheduled_end, status, priority, created_by, 
  location_building_id, location_level_id, location_room_no, is_outsourced
) VALUES (
  'CLEANING',
  'Daily cleaning with eco products',
  DATE_ADD(CURDATE(), INTERVAL 1 DAY) + INTERVAL 9 HOUR,
  DATE_ADD(CURDATE(), INTERVAL 1 DAY) + INTERVAL 11 HOUR,
  'SCHEDULED',
  2,
  (SELECT emp_id FROM Employee WHERE name='Bob Wong' LIMIT 1),
  (SELECT building_id FROM Building WHERE name='Block A' LIMIT 1),
  (SELECT l.level_id FROM Level l JOIN Building b ON b.building_id = l.building_id WHERE b.name='Block A' AND l.level_no=1 LIMIT 1),
  '101',
  TRUE
);

-- Window repair in Block B Level 2 today 14-16, no chemicals
INSERT INTO Activity (
  `type`, description, scheduled_start, scheduled_end, status, priority, created_by,
  location_building_id, location_level_id, location_room_no, is_outsourced
) VALUES (
  'MAINTENANCE',
  'Repair damaged window seals',
  CURDATE() + INTERVAL 14 HOUR,
  CURDATE() + INTERVAL 16 HOUR,
  'SCHEDULED',
  1,
  (SELECT emp_id FROM Employee WHERE name='Carol Lee' LIMIT 1),
  (SELECT building_id FROM Building WHERE name='Block B' LIMIT 1),
  (SELECT l.level_id FROM Level l JOIN Building b ON b.building_id = l.building_id WHERE b.name='Block B' AND l.level_no=2 LIMIT 1),
  NULL,
  FALSE
);

-- Link chemicals to cleaning activity
INSERT INTO ActivityChemical (activity_id, chemical_id, quantity)
SELECT a.activity_id, c.chemical_id, 2.5
FROM Activity a, Chemical c
WHERE a.description LIKE 'Daily cleaning%' AND c.name IN ('Eco Floor Soap','Chlorine Bleach')
ON DUPLICATE KEY UPDATE quantity=VALUES(quantity);

-- Assign workers
INSERT INTO Assignment (activity_id, emp_id, assigned_role, hours_assigned, status)
SELECT a.activity_id, p.emp_id, 'LEAD', 2.0, 'ASSIGNED'
FROM Activity a, Employee p
WHERE a.description LIKE 'Daily cleaning%' AND p.name='David Ng'
ON DUPLICATE KEY UPDATE assigned_role=VALUES(assigned_role), hours_assigned=VALUES(hours_assigned), status=VALUES(status);

INSERT INTO Assignment (activity_id, emp_id, assigned_role, hours_assigned, status)
SELECT a.activity_id, p.emp_id, 'MEMBER', 2.0, 'ASSIGNED'
FROM Activity a, Employee p
WHERE a.description LIKE 'Daily cleaning%' AND p.name='Eva Ho'
ON DUPLICATE KEY UPDATE assigned_role=VALUES(assigned_role), hours_assigned=VALUES(hours_assigned), status=VALUES(status);

-- Contract for the cleaning activity (outsourced)
INSERT INTO Contract (activity_id, contractor_id, contract_start, contract_end, cost)
SELECT a.activity_id, c.contractor_id, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 1 YEAR), 50000.00
FROM Activity a, Contractor c
WHERE a.description LIKE 'Daily cleaning%' AND c.company_name='CleanPro Services'
ON DUPLICATE KEY UPDATE contractor_id=VALUES(contractor_id), contract_start=VALUES(contract_start), contract_end=VALUES(contract_end), cost=VALUES(cost);
