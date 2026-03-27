"""
测试 cron 星期编码转换逻辑。

问题背景：
- APScheduler 的 CronTrigger.from_crontab() 使用 APScheduler 内部编码
- APScheduler 编码: 0=Monday, 1=Tuesday, ..., 6=Sunday
- 标准 cron 编码: 0=Sunday, 1=Monday, ..., 6=Saturday

重要发现：
- APScheduler 的 from_crontab() 使用 APScheduler 内部编码，而非标准 cron 编码
- 使用星期名称 (mon, tue, wed, thu, fri, sat, sun) 可以避免歧义
"""

from datetime import datetime

from apscheduler.triggers.cron import CronTrigger


class TestCronDayOfWeek:
    """测试 cron 星期编码处理"""

    def test_apscheduler_0_is_monday(self):
        """验证 APScheduler 中 0 表示周一"""
        # APScheduler 使用自己的编码: 0=Monday
        trigger = CronTrigger.from_crontab("0 9 * * 0")
        now = datetime.now()
        next_fire = trigger.get_next_fire_time(None, now)
        # 验证触发时间是周一
        assert next_fire.weekday() == 0  # Python datetime: 0=Monday

    def test_apscheduler_6_is_sunday(self):
        """验证 APScheduler 中 6 表示周日"""
        trigger = CronTrigger.from_crontab("0 9 * * 6")
        now = datetime.now()
        next_fire = trigger.get_next_fire_time(None, now)
        assert next_fire.weekday() == 6  # Python datetime: 6=Sunday

    def test_cron_0_4_means_monday_to_friday(self):
        """验证 0-4 表示周一到周五（APScheduler 编码）"""
        trigger = CronTrigger.from_crontab("0 9 * * 0-4")
        now = datetime.now()
        next_fire = trigger.get_next_fire_time(None, now)
        # 应该在周一到周五之间触发 (Python: 0-4)
        assert next_fire.weekday() in [0, 1, 2, 3, 4]

    def test_cron_mon_fri_means_monday_to_friday(self):
        """验证 mon-fri 正确表示周一到周五"""
        trigger = CronTrigger.from_crontab("0 9 * * mon-fri")
        now = datetime.now()
        next_fire = trigger.get_next_fire_time(None, now)
        # 应该在周一到周五之间触发 (Python: 0-4)
        assert next_fire.weekday() in [0, 1, 2, 3, 4]

    def test_cron_weekday_names_work_correctly(self):
        """验证星期名称可以正确解析"""
        # 测试各种星期名称组合
        test_cases = [
            ("mon", 0),   # Monday
            ("tue", 1),   # Tuesday
            ("wed", 2),   # Wednesday
            ("thu", 3),   # Thursday
            ("fri", 4),   # Friday
            ("sat", 5),   # Saturday
            ("sun", 6),   # Sunday
        ]

        for day_name, expected_weekday in test_cases:
            trigger = CronTrigger.from_crontab(f"0 9 * * {day_name}")
            now = datetime.now()
            next_fire = trigger.get_next_fire_time(None, now)
            assert next_fire.weekday() == expected_weekday, \
                f"Expected {day_name} to be weekday {expected_weekday}, got {next_fire.weekday()}"

    def test_cron_multiple_days_with_names(self):
        """验证多个星期名称用逗号分隔可以正确解析"""
        trigger = CronTrigger.from_crontab("0 9 * * mon,wed,fri")
        now = datetime.now()
        next_fire = trigger.get_next_fire_time(None, now)
        # 应该在周一、周三或周五触发
        assert next_fire.weekday() in [0, 2, 4]

    def test_weekdays_cron_should_not_fire_on_weekend(self):
        """验证工作日 cron 不应在周末触发"""
        trigger = CronTrigger.from_crontab("0 9 * * mon-fri")
        now = datetime.now()

        # 获取接下来 7 天的所有触发时间
        next_fire = now
        weekdays_triggered = set()
        for _ in range(10):  # 获取接下来 10 次触发
            next_fire = trigger.get_next_fire_time(None, next_fire)
            weekdays_triggered.add(next_fire.weekday())
            next_fire = next_fire.replace(second=next_fire.second + 1)

        # 确保没有周六(5)或周日(6)
        assert 5 not in weekdays_triggered, "Should not trigger on Saturday"
        assert 6 not in weekdays_triggered, "Should not trigger on Sunday"


class TestCronExpressionGeneration:
    """测试前端生成的 cron 表达式格式"""

    def test_weekdays_generates_mon_fri(self):
        """验证工作日模式生成 mon-fri"""
        # 模拟前端逻辑
        frequency = "weekdays"
        minute, hour = 30, 9

        if frequency == 'weekdays':
            cron = f"{minute} {hour} * * mon-fri"
        else:
            cron = f"{minute} {hour} * * *"

        assert cron == "30 9 * * mon-fri"

        # 验证可以被 APScheduler 正确解析
        trigger = CronTrigger.from_crontab(cron)
        assert trigger is not None

    def test_weekly_generates_correct_day_names(self):
        """验证每周特定时间模式生成正确的星期名称"""
        week_days = [0, 2, 4]  # 周一、周三、周五
        minute, hour = 30, 9

        day_names = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
        days = ','.join(day_names[d] for d in week_days)
        cron = f"{minute} {hour} * * {days}"

        assert cron == "30 9 * * mon,wed,fri"

        # 验证可以被 APScheduler 正确解析
        trigger = CronTrigger.from_crontab(cron)
        assert trigger is not None

    def test_daily_generates_standard_cron(self):
        """验证每天模式生成标准 cron"""
        frequency = "daily"
        minute, hour = 30, 9

        if frequency == 'daily':
            cron = f"{minute} {hour} * * *"
        else:
            cron = f"{minute} {hour} * * *"

        assert cron == "30 9 * * *"

        # 验证可以被 APScheduler 正确解析
        trigger = CronTrigger.from_crontab(cron)
        assert trigger is not None


class TestCronExpressionParsing:
    """测试编辑任务时的 cron 表达式解析"""

    def test_parse_mon_fri_as_weekdays(self):
        """验证 mon-fri 被解析为工作日模式"""
        cron = "30 9 * * mon-fri"
        parts = cron.split()
        dow = parts[4]

        frequency = None
        if dow == 'mon-fri':
            frequency = 'weekdays'

        assert frequency == 'weekdays'

    def test_parse_day_names_to_values(self):
        """验证星期名称转换为前端编码值"""
        cron = "30 9 * * mon,wed,fri"
        parts = cron.split()
        dow = parts[4]

        day_name_to_value = {'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6}

        if dow != '*' and dow != '?' and dow != 'mon-fri':
            week_days = [day_name_to_value[d] for d in dow.split(',')]
        else:
            week_days = []

        assert week_days == [0, 2, 4]  # 周一、周三、周五
