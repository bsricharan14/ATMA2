--tables
CREATE TABLE semesters (
    sem_id INT AUTO_INCREMENT PRIMARY KEY,
    sem_name VARCHAR(100) NOT NULL,
    sem_seed VARCHAR(100),
    start_time TIME,
    end_time TIME,
    working_days VARCHAR(255),
    slot_duration INT
);

CREATE TABLE classes (
    class_id INT AUTO_INCREMENT PRIMARY KEY,
    sem_id INT,
    class_name VARCHAR(100) NOT NULL,
    capacity INT NOT NULL,
    UNIQUE (sem_id, class_name),
    FOREIGN KEY (sem_id) REFERENCES semesters(sem_id) ON DELETE CASCADE
);

CREATE TABLE courses (
    course_id INT AUTO_INCREMENT PRIMARY KEY,
    sem_id INT,
    course_name VARCHAR(100) NOT NULL,
    num_students INT,
    max_minutes_per_week INT,
    max_minutes_per_day INT,
    min_minutes_per_day INT,
    course_abbr VARCHAR(255),
    FOREIGN KEY (sem_id) REFERENCES semesters(sem_id) ON DELETE CASCADE
);

CREATE TABLE timetable (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sem_id INT,
    class_id INT,
    day VARCHAR(10),
    slot_id INT,
    course_id INT,
    FOREIGN KEY (sem_id) REFERENCES semesters(sem_id) ON DELETE CASCADE,
    FOREIGN KEY (class_id) REFERENCES classes(class_id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses(course_id) ON DELETE CASCADE
);

CREATE TABLE break_timings (
    break_id INT AUTO_INCREMENT PRIMARY KEY,
    sem_id INT,
    break_name VARCHAR(100) NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    FOREIGN KEY (sem_id) REFERENCES semesters(sem_id) ON DELETE CASCADE
);
