--创建触发器和触发器函数
CREATE OR REPLACE FUNCTION set_student_id()
	RETURNS TRIGGER
	AS $$
DECLARE
	max_id int;
BEGIN
	SELECT
		COALESCE(MAX(student_id), 0) INTO max_id
	FROM
		student;
	NEW.student_id := max_id + 1;
	RETURN NEW;
END;
$$
LANGUAGE plpgsql;
--参考
CREATE OR REPLACE FUNCTION set_teacher_id()
	RETURNS TRIGGER
	AS $$
DECLARE
	max_id int;
BEGIN
	SELECT
		COALESCE(MAX(teacher_id), 0) INTO max_id
	FROM
		teacher;
	NEW.teacher_id := max_id + 1;
	RETURN NEW;
END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION set_classroom_id()
	RETURNS TRIGGER
	AS $$
DECLARE
	max_id int;
BEGIN
	SELECT
		COALESCE(MAX(room_id), 0) INTO max_id
	FROM
		classroom;
	NEW.room_id := max_id + 1;
	RETURN NEW;
END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION set_T_Dictionary_id()
	RETURNS TRIGGER
	AS $$
DECLARE
	max_id int;
BEGIN
	SELECT
		COALESCE(MAX(Dic_id), 0) INTO max_id
	FROM
		T_Dictionary;
	NEW.Dic_id := max_id + 1;
	RETURN NEW;
END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION set_task_id()
	RETURNS TRIGGER
	AS $$
DECLARE
	max_id int;
BEGIN
	SELECT
		COALESCE(MAX(task_id), 0) INTO max_id
	FROM
		task;
	NEW.task_id := max_id + 1;
	RETURN NEW;
END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION set_course_id()
	RETURNS TRIGGER
	AS $$
DECLARE
	max_id int;
BEGIN
	SELECT
		COALESCE(MAX(course_id), 0) INTO max_id
	FROM
		course;
	NEW.course_id := max_id + 1;
	RETURN NEW;
END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION set_task_schedule_id()
	RETURNS TRIGGER
	AS $$
DECLARE
	max_id int;
BEGIN
	SELECT
		COALESCE(MAX(schedule_id), 0) INTO max_id
	FROM
		task_schedule;
	NEW.schedule_id := max_id + 1;
	RETURN NEW;
END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION set_student_task_id()
	RETURNS TRIGGER
	AS $$
DECLARE
	max_id int;
BEGIN
	SELECT
		COALESCE(MAX(student_select_id), 0) INTO max_id
	FROM
		student_task;
	NEW.student_select_id := max_id + 1;
	RETURN NEW;
END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER student_insert_trigger
	BEFORE INSERT ON student
	FOR EACH ROW
	EXECUTE FUNCTION public.set_student_id();

CREATE OR REPLACE TRIGGER teacher_insert_trigger
	BEFORE INSERT ON teacher
	FOR EACH ROW
	EXECUTE FUNCTION public.set_teacher_id();

CREATE OR REPLACE TRIGGER classroom_insert_trigger
	BEFORE INSERT ON classroom
	FOR EACH ROW
	EXECUTE FUNCTION public.set_classroom_id();

CREATE OR REPLACE TRIGGER T_Dictionary_insert_trigger
	BEFORE INSERT ON T_Dictionary
	FOR EACH ROW
	EXECUTE FUNCTION public.set_T_Dictionary_id();

CREATE OR REPLACE TRIGGER task_insert_trigger
	BEFORE INSERT ON task
	FOR EACH ROW
	EXECUTE FUNCTION public.set_task_id();

CREATE OR REPLACE TRIGGER task_schedule_insert_trigger
	BEFORE INSERT ON task_schedule
	FOR EACH ROW
	EXECUTE FUNCTION public.set_task_schedule_id();

CREATE OR REPLACE TRIGGER course_insert_trigger
	BEFORE INSERT ON course
	FOR EACH ROW
	EXECUTE FUNCTION public.set_course_id();

CREATE OR REPLACE TRIGGER student_task_insert_trigger
	BEFORE INSERT ON student_task
	FOR EACH ROW
	EXECUTE FUNCTION public.set_student_task_id();















































-- 插入学生任务记录时，确保学生和任务存在
CREATE OR REPLACE FUNCTION check_student_task() RETURNS TRIGGER AS $$
BEGIN
    -- 检查学生是否存在
    IF NOT EXISTS (SELECT 1 FROM student WHERE student_id = NEW.student_id) THEN
        RAISE EXCEPTION '学生ID % 不存在', NEW.student_id;
    END IF;

    -- 检查任务是否存在
    IF NOT EXISTS (SELECT 1 FROM task WHERE task_id = NEW.task_id) THEN
        RAISE EXCEPTION '任务ID % 不存在', NEW.task_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 插入任务安排记录时，确保教室和任务存在，并避免时间冲突
CREATE OR REPLACE FUNCTION check_task_schedule() RETURNS TRIGGER AS $$
BEGIN
    -- 检查教室是否存在
    IF NOT EXISTS (SELECT 1 FROM classroom WHERE room_id = NEW.room_id) THEN
        RAISE EXCEPTION '教室ID % 不存在', NEW.room_id;
    END IF;

    -- 检查任务是否存在
    IF NOT EXISTS (SELECT 1 FROM task WHERE task_id = NEW.task_id) THEN
        RAISE EXCEPTION '任务ID % 不存在', NEW.task_id;
    END IF;

    -- 检查教室时间冲突
    IF EXISTS (
        SELECT 1 FROM task_schedule
        WHERE room_id = NEW.room_id
        AND NEW.start_week <= end_week
        AND NEW.end_week >= start_week
    ) THEN
        RAISE EXCEPTION '教室ID % 在周 % 到周 % 期间有时间冲突', NEW.room_id, NEW.start_week, NEW.end_week;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 在插入学生任务记录时调用 check_student_task 函数
CREATE TRIGGER trg_check_student_task
BEFORE INSERT ON student_task
FOR EACH ROW
EXECUTE FUNCTION check_student_task();

-- 在插入任务安排记录时调用 check_task_schedule 函数
CREATE TRIGGER trg_check_task_schedule
BEFORE INSERT ON task_schedule
FOR EACH ROW
EXECUTE FUNCTION check_task_schedule();

