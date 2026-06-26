from django.db import models


class Member(models.Model):
    member_no = models.AutoField(db_column='member_no', primary_key=True)
    member_id = models.CharField(db_column='member_id', max_length=20, unique=True)
    member_pwd = models.CharField(db_column='member_pwd', max_length=200)
    member_name = models.CharField(db_column='member_name', max_length=50)
    member_email = models.CharField(db_column='member_email', max_length=50)
    ROLE_CHOICES = [('admin', '관리자'), ('member', '일반회원')]
    FACILITY_CHOICES = [
        ('', '해당없음'),
        ('강남', '강남 자원회수시설'),
        ('노원', '노원 자원회수시설'),
        ('마포', '마포 자원회수시설'),
        ('양천', '양천 자원회수시설'),
    ]
    role = models.CharField(db_column='role', max_length=20, choices=ROLE_CHOICES, default='member')
    facility = models.CharField(db_column='facility', max_length=20, choices=FACILITY_CHOICES, default='', blank=True)
    usage_flag = models.CharField(db_column='usage_flag', max_length=10, default='1')
    register_date = models.DateTimeField(db_column='register_date', auto_now_add=True)
    access_latest = models.DateTimeField(db_column='access_latest', null=True, blank=True)

    class Meta:
        managed = True
        db_table = 'member'

    def __str__(self):
        return self.member_name + ' (' + self.member_id + ')'


class Suwontrash_all(models.Model):
    date = models.CharField(db_column='date', max_length=50)
    total = models.CharField(db_column='total', max_length=50)
    key_num = models.ForeignKey(Member, related_name='connect', on_delete=models.CASCADE, db_column='key_num')

    class Meta:
        db_table = 'suwontrash_all'
