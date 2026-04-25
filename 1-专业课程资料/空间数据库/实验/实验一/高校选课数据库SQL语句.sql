CREATE TABLE student (
    student_id INTEGER PRIMARY KEY,
    student_name CHARACTER(20) NOT NULL,
    student_gender BIT NOT NULL,
    student_major CHARACTER(20) NOT NULL,
    student_college CHARACTER(20) NOT NULL,
    student_age INTEGER NOT NULL,
	student_year INTEGER NOT NULL
);

CREATE TABLE teacher (
    teacher_id INTEGER PRIMARY KEY,
    teacher_name CHARACTER(20) NOT NULL,
    teacher_gender BIT NOT NULL,
    teacher_age INTEGER NOT NULL,
    teacher_introduce CHARACTER(20) NOT NULL
);

CREATE TABLE course (
    course_id INTEGER PRIMARY KEY,
    course_name CHARACTER(20) NOT NULL,
    course_score DOUBLE PRECISION NOT NULL,
    theory_hours INTEGER NOT NULL,
    lab_hours INTEGER NOT NULL,
    practice_hours INTEGER NOT NULL,
    course_type INTEGER NOT NULL,
    course_content TEXT NOT NULL,
    course_object TEXT NOT NULL
);

CREATE TABLE T_dictionary (
    Dic_id INTEGER PRIMARY KEY,
	Dic_type CHARACTER(20) NOT NULL,
    Dic_key INTEGER NOT NULL,
    key_value CHARACTER(20) NOT NULL
);

CREATE TABLE classroom (
    room_id INTEGER PRIMARY KEY,
    building_name CHARACTER(20) NOT NULL,
    capacity INTEGER NOT NULL,
	door_number CHARACTER(20)
    
);


CREATE TABLE task (
    task_id INTEGER PRIMARY KEY,
    teacher_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    year_semtember INTEGER NOT NULL,
    course_hour INTEGER NOT NULL,
    student_count INTEGER NOT NULL,
    FOREIGN KEY (teacher_id) REFERENCES teacher(teacher_id),
    FOREIGN KEY (course_id) REFERENCES course(course_id)
);

CREATE TABLE task_schedule (
    schedule_id INTEGER PRIMARY KEY,
    room_id INTEGER NOT NULL,
    task_id INTEGER NOT NULL,
    start_week INTEGER NOT NULL,
    end_week INTEGER NOT NULL,
    FOREIGN KEY (room_id) REFERENCES classroom(room_id), 
    FOREIGN KEY (task_id) REFERENCES task(task_id)
);

CREATE TABLE student_task (
    student_select_id INTEGER PRIMARY KEY,
    student_id INTEGER NOT NULL,
    task_id INTEGER NOT NULL,
    course_score INTEGER NOT NULL,
    lab_record DOUBLE PRECISION NOT NULL,
    total_record DOUBLE PRECISION NOT NULL,
    FOREIGN KEY (student_id) REFERENCES student(student_id),
    FOREIGN KEY (task_id) REFERENCES task(task_id)
);


