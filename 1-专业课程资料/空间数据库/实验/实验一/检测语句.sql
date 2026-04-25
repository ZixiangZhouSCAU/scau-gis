--执行insert时触发该触发器自动填student_id
INSERT INTO student(student_name, student_gender, student_major, student_year, student_college,student_age)
	VALUES
('蔡中现', B'0', 1, 2023, 1,19),
('陈阳', B'1', 2, 2023, 1,19),
('黄超', B'0', 2, 2023, 1,20),
('蔡毅奚', B'0', 3, 2023, 1,19),
('龙福成', B'0', 1, 2023, 1,21),
('邓一山', B'1', 2, 2023, 1,19),
('白恩', B'0', 3, 2023, 1,19),
('黄行', B'0', 2, 2023, 1,19),
('莫蔷薇', B'1', 2, 2023, 1,19),
('江权', B'1', 1, 2023, 1,20);

INSERT INTO teacher(teacher_name, teacher_gender, teacher_age, teacher_introduce)
	VALUES
('蒋光图', B'0', 53, '测绘与地理信息系教授'),
('陈诗', B'1', 38, '测绘与地理信息系辅导员'),
('周健封', B'0', 54, '测绘与地理信息系副教授'),
('周用', B'0', 53, '测绘与地理信息系副教授'),
('奕林', B'0', 35, '体育与健康系副教授'),
('刘丹陈', B'1', 45, '数学系教授'),
('舒篇', B'0', 50, '大气科学系讲师'),
('陈汉理', B'0', 34, '测绘与地理信息系讲师'),
('张机', B'0', 57, '测绘与地理信息系教授'),
('马远志', B'0', 60, '测绘与地理信息系副教授'),
('邓崇', B'1', 43, '外语系教授');

INSERT INTO course(course_name,course_score,theory_hours,lab_hours,practice_hours,course_type,course_content,course_object)
	VALUES
('空间数据库原理与应用',2.5,48,16,8,1,'学习空间数据的存储、查询与分析','2023级地理信息科学专业学生'),
('测量学',4,64,32,8,1,'学习测量原理、技术、方法、仪器、数据处理。','2023级地理信息科学专业学生'),
('大气科学',2,32,0,0,2,'研究地球大气层及其与地球系统其他部分相互作用的科学。','2023级地理信息科学专业学生'),
('GIS软件开发',4,64,32,8,1,'系统设计、编程、空间数据库、用户界面。','2023级地理信息科学专业学生'),
('大学英语',2,48,0,0,1,'学习高等英语写作。','2023级地理信息科学专业学生'),
('空间分析',4,64,32,8,1,'地理建模、数据挖掘、空间统计、GIS应用。','2023级地理信息科学专业学生'),
('大学体育',2,32,32,0,1,'学习基础体育健康知识','2023级地理信息科学专业学生'),
('生涯职业规划',2,32,0,0,1,'学习对专业就业的基础知识','2023级地理信息科学专业学生'),
('Java程序开发',4,64,32,8,2,'学习面向对象编程思想','2023级地理信息科学专业学生'),
('遥感导论',3,44,32,0,2,'学习遥感的基础概念','2023级地理信息科学专业学生');

INSERT INTO classroom(building_name,door_number,capacity)
VALUES
('第五教学楼B栋','5B231',102),
('第五教学楼D栋','5D411',65),
('第五教学楼D栋','5D406',133),
('第五教学楼C栋','5C701',77),
('第五教学楼C栋','5C107',85),
('第五教学楼B栋','5B111',93),
('第五教学楼B栋','5B202',123),
('第五教学楼D栋','5D623',147),
('第五教学楼D栋','5D233',63),
('第五教学楼C栋','5C811',190);

INSERT INTO task (teacher_id, course_id, year_semtember, course_hour, student_count) 
VALUES 
(1,1,2023,48,40),
(2,8,2023,48,55),
(3,4,2024,48,34),
(4,2,2023,64,80),
(10,5,2024,48,53),
(5,7,2023,48,64),
(7,3,2023,32,88),
(6,9,2024,64,99),
(8,6,2023,64,102),
(9,10,2023,44,98);

INSERT INTO task_schedule (room_id, task_id, start_week, end_week) 
VALUES 
(1, 1, 1, 14),  -- 教室1，任务1，从第1周到第14周
(2, 1, 14, 16), -- 教室2，任务1，从第14周到第16周
(3, 3, 1, 16),  -- 教室3，任务3，从第1周到第16周
(4, 2, 4, 8),  -- 教室4，任务2，从第4周到第8周
(1, 4, 15, 16), -- 教室1，任务4，从第15周到第16周
(2, 5, 1, 13), -- 教室2，任务5，从第1周到第13周
(5, 3, 4, 6),  -- 教室5，任务6，从第1周到第16周
(6, 9, 9, 12),  -- 教室6，任务9，从第9周到第12周
(7, 8, 11, 15),  -- 教室7，任务8，从第11周到第15周
(9, 7, 15, 16); -- 教室9，任务7，从第15周到第16周



INSERT INTO student_task (student_id, task_id, course_score, lab_record, total_record) 
VALUES 
(1, 1, 85, 90.5, 88.0),   -- 学生1选择任务1
(1, 2, 88, 89.0, 88.5),   -- 学生1选择任务2
(2, 1, 78, 85.0, 80.0),   -- 学生2选择任务1
(3, 2, 92, 95.0, 94.0),   -- 学生3选择任务2
(4, 4, 75, 80.0, 77.5),   -- 学生4选择任务4
(5, 3, 90, 88.0, 89.0),   -- 学生5选择任务3
(1, 3, 82, 85.0, 83.5),   -- 学生1再次选择任务3
(2, 2, 74, 79.0, 76.5),   -- 学生2选择任务2
(3, 5, 91, 92.0, 91.0),   -- 学生3选择任务5
(4, 10, 80, 82.0, 81.0);  -- 学生4选择任务10


-- 创建一个名为 student_schedule 的视图，检索学生的课程表
CREATE VIEW student_schedule AS
SELECT 
    s.student_name,  -- 选择学生的姓名
    c.course_name,    -- 选择课程的名称
    ts.start_week,    -- 选择任务安排的开始周
    ts.end_week       -- 选择任务安排的结束周
FROM 
    student s  -- 从学生表 (student) 中获取数据，使用别名 s
JOIN 
    student_task st ON s.student_id = st.student_id  -- 连接学生表和学生任务表，匹配学生ID
JOIN 
    task t ON st.task_id = t.task_id  -- 连接学生任务表和任务表，按任务ID进行匹配
JOIN 
    task_schedule ts ON t.task_id = ts.task_id  -- 连接任务表和任务安排表，按任务ID进行匹配
JOIN 
    course c ON t.course_id = c.course_id  -- 连接任务表和课程表，按课程ID进行匹配
WHERE 
    s.student_id = 1 AND -- 筛选出特定学生的课程安排，学生ID为1（可根据需要替换为其他学生ID）
    t.year_semtember = 2023; -- 筛选出特定学期的课程安排，这里筛选的是2023学年和学期

select * from student_schedule;

-- 创建一个名为 course_schedule 的视图，检索课程的信息
CREATE VIEW course_schedule AS
SELECT 
    -- 选择课程的ID
    co.course_id,
    -- 选择课程的名称
    co.course_name,
    -- 选择与课程相关的任务的ID
    ta.task_id,
    -- 选择任务安排中的教室ID
    sc.room_id,
    -- 选择任务开始的周数
    sc.start_week,
    -- 选择任务结束的周数
    sc.end_week
FROM 
    -- 从课程表中获取数据，使用别名 co
    course co
JOIN 
    -- 将任务表与课程表进行连接，使用别名 ta
    task ta ON co.course_id = ta.course_id
JOIN 
    -- 将任务安排表与任务表进行连接，使用别名 sc
    task_schedule sc ON ta.task_id = sc.task_id;

select * from course_schedule;

-- 创建一个名为 teacher_student_performance 的视图,检索学生的成绩
CREATE VIEW teacher_student_performance AS
SELECT 
    -- 选择教师的ID
    te.teacher_id,
    -- 选择教师的姓名
    te.teacher_name,
    -- 选择学生的ID
    s.student_id,
    -- 选择学生的姓名
    s.student_name,
    -- 选择学生在相关任务中的课程成绩
    st.course_score,
    -- 选择任务的ID
    ta.task_id,
    -- 选择课程的名称
    co.course_name
FROM 
    -- 从教师表中获取数据，使用别名 te
    teacher te
JOIN 
    -- 将任务表与教师表进行连接，使用别名 ta
    task ta ON te.teacher_id = ta.teacher_id
JOIN 
    -- 将学生任务表与任务表进行连接，使用别名 st
    student_task st ON ta.task_id = st.task_id
JOIN 
    -- 将学生表与学生任务表进行连接，使用别名 s
    student s ON st.student_id = s.student_id
JOIN 
    -- 将课程表与任务表进行连接，使用别名 co
    course co ON ta.course_id = co.course_id;

SELECT * FROM teacher_student_performance;
